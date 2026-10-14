"""Build the E6 reviewer-reply packet for one source (amendment A2 delivery)."""
import hashlib, json, pathlib, sys
sid = sys.argv[1]
d = pathlib.Path('reference', sid)
author = json.loads((d / 'AUTHOR-PACKET.json').read_text(encoding='utf-8'))
load = lambda n: json.loads((d / n).read_bytes())
sha = lambda n: hashlib.sha256((d / n).read_bytes()).hexdigest()
pk = {'packet': 'r17.reference-reply-packet.v1', 'source_id': sid,
      'reference_spec': author['reference_spec'], 'source_text': author['source_text'],
      'your_review': load('REVIEW-1.json'), 'author_response': load('RESPONSE-1.json'),
      'revised_draft': load('draft-2.json'), 'revised_draft_sha256': sha('draft-2.json'),
      'response_sha256': sha('RESPONSE-1.json')}
b = (json.dumps(pk, ensure_ascii=False, indent=1) + '\n').encode('utf-8')
(d / 'REPLY-PACKET.json').write_bytes(b)
print(hashlib.sha256(b).hexdigest())
