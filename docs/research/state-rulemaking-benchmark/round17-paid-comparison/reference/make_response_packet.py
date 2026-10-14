"""Build the E6 author-response packet for one source (amendment A2 delivery)."""
import hashlib, json, pathlib, sys
sid = sys.argv[1]
d = pathlib.Path('reference', sid)
author = json.loads((d / 'AUTHOR-PACKET.json').read_text(encoding='utf-8'))
draft = (d / 'draft-1.json').read_bytes()
review = (d / 'REVIEW-1.json').read_bytes()
pk = {'packet': 'r17.reference-response-packet.v1', 'source_id': sid,
      'source_text_sha256': author['source_text_sha256'], 'reference_spec': author['reference_spec'],
      'source_text': author['source_text'], 'your_draft': json.loads(draft),
      'your_draft_sha256': hashlib.sha256(draft).hexdigest(), 'review': json.loads(review),
      'review_sha256': hashlib.sha256(review).hexdigest()}
b = (json.dumps(pk, ensure_ascii=False, indent=1) + '\n').encode('utf-8')
(d / 'RESPONSE-PACKET.json').write_bytes(b)
print(hashlib.sha256(b).hexdigest())
