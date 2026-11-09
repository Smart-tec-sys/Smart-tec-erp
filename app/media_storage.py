"""Armazenamento das imagens de empresa e usuário (logo e avatar).

As URLs públicas continuam no formato ``/media/<chave>``; a chave é o caminho
relativo dentro do armazenamento (pasta local ou bucket privado do Supabase).
"""
import os
import re
import uuid
from pathlib import Path
from urllib.parse import quote

import requests

TAMANHO_MAXIMO_IMAGEM = 5 * 1024 * 1024
TIPOS_PERMITIDOS = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}
TIPO_POR_EXTENSAO = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}
PREFIXO_URL = "/media/"
_CHAVE_VALIDA = re.compile(
    r"^(empresas|usuarios)/(?:[0-9]+/)?[A-Za-z0-9][A-Za-z0-9_-]{0,150}\.(jpg|jpeg|png|webp)$"
)
_SESSAO_HTTP = requests.Session()


class MediaStorageError(RuntimeError):
    pass


class MediaNaoEncontrada(MediaStorageError):
    pass


class ImagemInvalida(ValueError):
    pass


def chave_valida(chave: str) -> bool:
    return isinstance(chave, str) and bool(_CHAVE_VALIDA.fullmatch(chave))


def tipo_da_chave(chave: str) -> str:
    return TIPO_POR_EXTENSAO[Path(chave).suffix.lower()]


def url_publica(chave: str) -> str:
    return PREFIXO_URL + chave


def chave_da_url(url: str | None) -> str | None:
    if not url or not url.startswith(PREFIXO_URL):
        return None
    chave = url[len(PREFIXO_URL):]
    return chave if chave_valida(chave) else None


def validar_imagem(content_type: str | None, conteudo: bytes) -> str:
    extensao = TIPOS_PERMITIDOS.get(content_type or "")
    if extensao is None:
        raise ImagemInvalida("formato de imagem não permitido")
    if not conteudo:
        raise ImagemInvalida("arquivo vazio")
    if len(conteudo) > TAMANHO_MAXIMO_IMAGEM:
        raise ImagemInvalida("imagem deve ter no máximo 5 MB")
    assinatura_ok = {
        "image/jpeg": conteudo.startswith(b"\xff\xd8\xff"),
        "image/png": conteudo.startswith(b"\x89PNG\r\n\x1a\n"),
        "image/webp": conteudo[:4] == b"RIFF" and conteudo[8:12] == b"WEBP",
    }[content_type]
    if not assinatura_ok:
        raise ImagemInvalida("conteúdo do arquivo não corresponde ao formato informado")
    return extensao


def pertence_ao_dono(chave: str | None, pasta: str, dono_id: int, prefixo_legado: str) -> bool:
    """Formato novo ``pasta/<id>/...`` ou legado ``pasta/<prefixo>-<id>-...``."""
    if not chave or not chave_valida(chave):
        return False
    return chave.startswith(f"{pasta}/{dono_id}/") or chave.startswith(
        f"{pasta}/{prefixo_legado}-{dono_id}-"
    )


class LocalMediaStorage:
    def __init__(self, raiz: str | Path):
        self.raiz = Path(raiz)

    def _caminho(self, chave: str) -> Path:
        if not chave_valida(chave):
            raise MediaNaoEncontrada(chave)
        return self.raiz / chave

    def salvar(self, chave: str, conteudo: bytes, content_type: str) -> None:
        caminho = self._caminho(chave)
        caminho.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(caminho, "xb") as arquivo:
                arquivo.write(conteudo)
        except OSError as exc:
            raise MediaStorageError("falha ao gravar imagem local") from exc

    def ler(self, chave: str) -> bytes:
        caminho = self._caminho(chave)
        if not caminho.is_file():
            raise MediaNaoEncontrada(chave)
        return caminho.read_bytes()

    def remover(self, chave: str) -> None:
        try:
            self._caminho(chave).unlink(missing_ok=True)
        except (OSError, MediaNaoEncontrada):
            pass


def _status_storage(resposta) -> int:
    # O Storage responde HTTP 400 com o status real no corpo (ex.: "404" objeto ausente, "403" chave inválida).
    if resposta.status_code != 400:
        return resposta.status_code
    try:
        return int(resposta.json().get("statusCode"))
    except (ValueError, TypeError, AttributeError):
        return 400


class SupabaseMediaStorage:
    def __init__(self, url: str, chave_secreta: str, bucket: str, timeout: float = 15, sessao=None):
        self.url = url.rstrip("/")
        self.bucket = bucket
        self.timeout = timeout
        self.sessao = sessao or _SESSAO_HTTP
        self._headers = {"apikey": chave_secreta, "Authorization": f"Bearer {chave_secreta}"}

    def __repr__(self):
        return f"SupabaseMediaStorage(url={self.url!r}, bucket={self.bucket!r}, chave=<redacted>)"

    def _objeto(self, chave: str, autenticado: bool = False) -> str:
        if not chave_valida(chave):
            raise MediaNaoEncontrada(chave)
        trecho = "object/authenticated" if autenticado else "object"
        return f"{self.url}/storage/v1/{trecho}/{quote(self.bucket)}/{quote(chave)}"

    def _requisicao(self, metodo: str, url: str, **kwargs):
        try:
            return self.sessao.request(metodo, url, headers={**self._headers, **kwargs.pop("headers", {})},
                                       timeout=self.timeout, **kwargs)
        except requests.RequestException as exc:
            raise MediaStorageError("armazenamento de imagens indisponível") from exc

    def salvar(self, chave: str, conteudo: bytes, content_type: str) -> None:
        resposta = self._requisicao("POST", self._objeto(chave), data=conteudo, headers={
            "Content-Type": content_type, "x-upsert": "false", "cache-control": "86400",
        })
        if resposta.status_code not in (200, 201):
            raise MediaStorageError(f"falha ao gravar imagem no Storage (HTTP {resposta.status_code})")

    def ler(self, chave: str) -> bytes:
        resposta = self._requisicao("GET", self._objeto(chave, autenticado=True))
        if _status_storage(resposta) == 404:
            raise MediaNaoEncontrada(chave)
        if resposta.status_code != 200:
            raise MediaStorageError(f"falha ao ler imagem do Storage (HTTP {resposta.status_code})")
        return resposta.content

    def remover(self, chave: str) -> None:
        if not chave_valida(chave):
            return
        try:
            self._requisicao("DELETE", f"{self.url}/storage/v1/object/{quote(self.bucket)}",
                             json={"prefixes": [chave]})
        except MediaStorageError:
            pass


def validar_configuracao_media() -> str:
    modo = os.getenv("SMARTTEC_MEDIA_STORAGE", "local").strip().lower() or "local"
    if modo not in {"local", "supabase"}:
        raise RuntimeError("SMARTTEC_MEDIA_STORAGE inválido. Use 'local' ou 'supabase'.")
    if modo == "supabase":
        obrigatorias = ("SUPABASE_STORAGE_URL", "SUPABASE_STORAGE_SECRET_KEY", "SUPABASE_STORAGE_BUCKET")
        ausentes = [nome for nome in obrigatorias if not os.getenv(nome, "").strip()]
        if ausentes:
            raise RuntimeError("Configuração do Supabase Storage incompleta. Ausentes: " + ", ".join(ausentes))
        if not os.environ["SUPABASE_STORAGE_URL"].strip().startswith("https://"):
            raise RuntimeError("SUPABASE_STORAGE_URL deve usar https.")
    return modo


def obter_media_storage():
    if validar_configuracao_media() == "supabase":
        return SupabaseMediaStorage(
            os.environ["SUPABASE_STORAGE_URL"].strip(),
            os.environ["SUPABASE_STORAGE_SECRET_KEY"].strip(),
            os.environ["SUPABASE_STORAGE_BUCKET"].strip(),
        )
    return LocalMediaStorage(os.getenv("SMARTTEC_MEDIA_DIR", "").strip() or "media")


def trocar_imagem(db, registro, campo: str, *, conteudo: bytes, content_type: str | None,
                  pasta: str, dono_id: int, prefixo_legado: str, nome: str, storage=None) -> str:
    """Grava a nova imagem, confirma a referência no banco e só então remove a antiga."""
    extensao = validar_imagem(content_type, conteudo)
    storage = storage or obter_media_storage()
    nova_chave = f"{pasta}/{dono_id}/{nome}-{uuid.uuid4().hex}{extensao}"
    storage.salvar(nova_chave, conteudo, content_type)
    chave_antiga = chave_da_url(getattr(registro, campo))
    setattr(registro, campo, url_publica(nova_chave))
    try:
        db.commit()
        db.refresh(registro)
    except Exception:
        db.rollback()
        storage.remover(nova_chave)
        raise
    if chave_antiga != nova_chave and pertence_ao_dono(chave_antiga, pasta, dono_id, prefixo_legado):
        storage.remover(chave_antiga)
    return getattr(registro, campo)


def remover_imagem(db, registro, campo: str, *, pasta: str, dono_id: int, prefixo_legado: str,
                   storage=None) -> None:
    chave_antiga = chave_da_url(getattr(registro, campo))
    setattr(registro, campo, None)
    try:
        db.commit()
        db.refresh(registro)
    except Exception:
        db.rollback()
        raise
    if pertence_ao_dono(chave_antiga, pasta, dono_id, prefixo_legado):
        (storage or obter_media_storage()).remover(chave_antiga)
