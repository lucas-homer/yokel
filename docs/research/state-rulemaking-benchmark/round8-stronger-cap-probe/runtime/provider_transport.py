"""Single real POST transport. Only called by explicitly authorized live runner."""
import ssl,urllib.error,urllib.request
ENDPOINTS={'jev':'https://api.typesafe.ai/v1/systemone','openrouter':'https://openrouter.ai/api/v1/chat/completions'}
class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):raise RuntimeError('provider redirect forbidden')
def post_once(provider,payload,key):
    import json
    if provider not in ENDPOINTS:raise ValueError('unsupported provider')
    body=json.dumps(payload,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
    request=urllib.request.Request(ENDPOINTS[provider],data=body,method='POST',headers={'Authorization':'Bearer '+key,'Content-Type':'application/json'})
    opener=urllib.request.build_opener(NoRedirect(),urllib.request.HTTPSHandler(context=ssl.create_default_context()))
    try:
        with opener.open(request,timeout=180 if provider=='openrouter' else 45) as response:return response.status,response.read(2_000_001)
    except urllib.error.HTTPError as error:return error.code,error.read(2_000_001)
