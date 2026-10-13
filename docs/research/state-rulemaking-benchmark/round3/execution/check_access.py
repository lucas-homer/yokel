import os,json,urllib.request,urllib.error
from pathlib import Path
request=urllib.request.Request('https://api.typesafe.ai/v1/models',headers={'Authorization':'Bearer '+os.environ['TYPESAFE_API_KEY']})
try:
 with urllib.request.urlopen(request,timeout=30) as response:
  payload=json.load(response)
  result={'http_status':response.status,'response':payload}
except urllib.error.HTTPError as error:
 result={'http_status':error.code}
Path(__file__).with_name('typesafe-access.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
