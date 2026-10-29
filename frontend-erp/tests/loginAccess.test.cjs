const assert=require('node:assert/strict')
const {registerHooks}=require('node:module')
const {pathToFileURL}=require('node:url')
const path=require('node:path')
const {stripTypeScriptTypes}=require('node:module')
const env={VITE_AUTH_MODE:'authenticated',VITE_SUPABASE_URL:'https://auth.test.invalid',VITE_SUPABASE_PUBLISHABLE_KEY:'test-only',VITE_API_URL:'https://api.test.invalid'}
registerHooks({load(url,context,next){
 const result=next(url,context)
 if(url.endsWith('/src/services/auth.ts')) return {...result,format:'module',source:stripTypeScriptTypes(String(result.source).replaceAll('import.meta.env',JSON.stringify(env)))}
 return result
}})
const storage=new Map()
global.sessionStorage={getItem:key=>storage.get(key)??null,setItem:(key,val)=>storage.set(key,val),removeItem:key=>storage.delete(key)}
;(async()=>{
 const auth=await import(pathToFileURL(path.join(__dirname,'../src/services/auth.ts')))
 const {resolveLoginAccess,LoginAccessError}=await import(pathToFileURL(path.join(__dirname,'../src/utils/loginAccess.ts')))
 const requests=[]
 let mode='valid', failProfile=false, failSecurity=false
 global.fetch=async(url,options)=>{
  const target=new URL(url);requests.push(target.pathname+target.search)
  if(target.hostname==='auth.test.invalid' && target.pathname==='/auth/v1/token'){
   if(mode==='invalid') return Response.json({msg:'Invalid login credentials'},{status:400})
   return Response.json({access_token:'TEST_ACCESS',refresh_token:'TEST_REFRESH',expires_in:3600})
  }
  if(target.hostname==='auth.test.invalid' && target.pathname==='/auth/v1/user'){
   if(failSecurity) return Response.json({msg:'Invalid login credentials'},{status:503})
   return Response.json({factors:[]})
  }
  if(target.hostname==='api.test.invalid' && target.pathname==='/auth/me'){
   assert.equal(options.headers.Authorization,'Bearer TEST_ACCESS')
   if(failProfile) return Response.json({detail:'unavailable'},{status:503})
   return Response.json({user:{id:7,email:'user@test.invalid'},empresas:[{id:3,nome:'Empresa teste',papel:'ADMIN'}]})
  }
  throw new Error('Unexpected test-only request')
 }
 const steps={factors:auth.listMfaFactors,challenge:auth.challengeTotpMfa,profile:auth.initializeAuthenticatedSession,markProfile:()=>auth.setPendingLoginStage('profile')}
 await auth.loginWithPassword(' USER@TEST.INVALID ','test-only-password')
 assert.equal(auth.getPendingLoginStage(),'security')
 const ready=await resolveLoginAccess(steps,true)
 assert.equal(ready.kind,'ready');assert.equal(ready.session.empresa.id,3)
 auth.setPendingLoginStage(undefined)
 assert.equal(auth.hasStoredAuthSession(),true)
 // Reload bootstrap can initialize directly from the persisted session without a second password grant.
 const passwordGrants=requests.filter(p=>p.includes('grant_type=password')).length
 assert.equal((await auth.initializeAuthenticatedSession()).user.id,7)
 assert.equal(requests.filter(p=>p.includes('grant_type=password')).length,passwordGrants)
 auth.clearAuthSession();assert.equal(auth.hasStoredAuthSession(),false)
 mode='invalid'
 await assert.rejects(auth.loginWithPassword('user@test.invalid','invalid-test-password'),/Invalid login credentials/)
 assert.equal(auth.hasStoredAuthSession(),false)
 mode='valid';await auth.loginWithPassword('user@test.invalid','test-only-password')
 failProfile=true
 await assert.rejects(resolveLoginAccess(steps,true),error=>error instanceof LoginAccessError && error.stage==='profile' && /Login confirmado/.test(error.message) && /GET https:\/\/api.test.invalid\/auth\/me: HTTP 503. unavailable/.test(error.message))
 assert.equal(auth.hasStoredAuthSession(),true);assert.equal(auth.getPendingLoginStage(),'profile')
 failProfile=false
 assert.equal((await resolveLoginAccess(steps,false)).kind,'ready')
 failSecurity=true;auth.setPendingLoginStage('security')
 await assert.rejects(resolveLoginAccess(steps,true),error=>error.stage==='security' && !/Invalid login credentials/.test(error.message))
 assert.equal(auth.getPendingLoginStage(),'security');assert.equal(auth.hasStoredAuthSession(),true)
 failSecurity=false
 let profileCalled=false
 const mfa=await resolveLoginAccess({factors:async()=>[{id:'factor',status:'verified',factor_type:'totp'}],challenge:async()=>({id:'challenge'}),profile:async()=>{profileCalled=true},markProfile:()=>{}},true)
 assert.equal(mfa.kind,'mfa');assert.equal(profileCalled,false)
 await assert.rejects(resolveLoginAccess({factors:async()=>{throw new Error('network')},challenge:async()=>({}),profile:async()=>{profileCalled=true},markProfile:()=>{}},true),error=>error.stage==='security')
 assert.equal(profileCalled,false)
 // Post-MFA bootstrap must use B, never the pre-MFA token A.
 sessionStorage.setItem('smarttec.erp.auth.v1',JSON.stringify({accessToken:'TOKEN_A',refreshToken:'REFRESH_A',expiresAt:Date.now()+3600000,loginStage:'security'}))
 let invalidMfa=true, omitMfaSession=false
 const profileTokens=[]
 global.fetch=async(url,options)=>{
  if(String(url).endsWith('/factors/factor/verify')) {
   assert.equal(options.headers.Authorization,'Bearer TOKEN_A')
   if(invalidMfa) return Response.json({msg:'Invalid TOTP code'},{status:422})
   if(omitMfaSession) return Response.json({})
   return Response.json({access_token:'TOKEN_B',refresh_token:'REFRESH_B',expires_in:3600})
  }
  if(String(url).endsWith('/auth/me')) {
   profileTokens.push(options.headers.Authorization)
   return Response.json({user:{id:7},empresas:[{id:3,nome:'Teste',papel:'ADMIN'}]})
  }
  throw new Error('Unexpected MFA test request')
 }
 await assert.rejects(auth.verifyTotpMfa('factor','challenge','123456'),/Invalid TOTP/)
 assert.equal(await auth.getAccessToken(),'TOKEN_A')
 invalidMfa=false;omitMfaSession=true
 await assert.rejects(auth.verifyTotpMfa('factor','challenge','123456'),/não retornou uma sessão válida/)
 assert.equal(profileTokens.length,0)
 omitMfaSession=false
 const verified=await auth.verifyTotpMfa('factor','challenge','123456')
 assert.equal(verified.accessToken,'TOKEN_B')
 await auth.initializeAuthenticatedSession(verified.accessToken)
 // Reload uses the persisted post-MFA token too.
 await auth.initializeAuthenticatedSession()
 assert.deepEqual(profileTokens,['Bearer TOKEN_B','Bearer TOKEN_B'])
 auth.clearAuthSession();assert.equal(auth.hasStoredAuthSession(),false)
 // A token refresh preserves the step needed to resume login safely.
 sessionStorage.setItem('smarttec.erp.auth.v1',JSON.stringify({accessToken:'old',refreshToken:'TEST_REFRESH',expiresAt:0,loginStage:'security'}))
 global.fetch=async()=>Response.json({access_token:'refreshed',refresh_token:'rotated',expires_in:3600})
 await auth.getAccessToken();assert.equal(auth.getPendingLoginStage(),'security')
 // A delayed refresh after logout must not resurrect the previous session.
 sessionStorage.setItem('smarttec.erp.auth.v1',JSON.stringify({accessToken:'old',refreshToken:'OLD_REFRESH',expiresAt:0,loginStage:'profile'}))
 let release
 global.fetch=()=>new Promise(resolve=>{release=()=>resolve(Response.json({access_token:'old-new',refresh_token:'OLD_ROTATED',expires_in:3600}))})
 const lateRefresh=auth.getAccessToken()
 auth.clearAuthSession();release()
 await assert.rejects(lateRefresh,/Sessão substituída/)
 assert.equal(auth.hasStoredAuthSession(),false)
 // Remote logout completes before local session removal; errors preserve retry.
 sessionStorage.setItem('smarttec.erp.auth.v1',JSON.stringify({accessToken:'LOGOUT_TOKEN',refreshToken:'LOGOUT_REFRESH',expiresAt:Date.now()+3600000}))
 let logoutFails=true, logoutCalls=0
 global.fetch=async(url,options)=>{
  assert.equal(String(url),'https://auth.test.invalid/auth/v1/logout?scope=global')
  assert.equal(options.method,'POST')
  assert.equal(options.headers.Authorization,'Bearer LOGOUT_TOKEN')
  assert.equal(auth.hasStoredAuthSession(),true)
  logoutCalls++
  return new Response(null,{status:logoutFails?503:204})
 }
 await assert.rejects(auth.signOut(),/HTTP 503/)
 assert.equal(auth.hasStoredAuthSession(),true)
 logoutFails=false
 await auth.signOut()
 assert.equal(logoutCalls,2)
 assert.equal(auth.hasStoredAuthSession(),false)
 await assert.rejects(auth.getAccessToken())
 // Reload finds no stored session; sign-out is idempotent locally.
 await auth.signOut();assert.equal(logoutCalls,2)
 global.fetch=async()=>Response.json({access_token:'NEW_LOGIN',refresh_token:'NEW_REFRESH',expires_in:3600})
 await auth.loginWithPassword('user@test.invalid','test-only-password')
 assert.equal(await auth.getAccessToken(),'NEW_LOGIN')
 auth.clearAuthSession()
 console.log('Login: sucesso sem novo grant, senha inválida, F5 persistido, logout/login, retry de perfil, erro MFA distinto, segurança sem bypass e refresh tardio aprovados.')
})().catch(err=>{console.error(err);process.exitCode=1})
