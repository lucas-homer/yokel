import copy, unittest
import pipeline as p
import development_fixtures as f

class Controls(unittest.TestCase):
    def date_fixture(self, raw, value):
        source=p.make_source('Comments close '+raw+'.','date-control')
        inv=f.empty_inventory(source)
        inv['events']=[f.event('comment','written_comment',source['source_text'],[f.timing('close',raw,value)])]
        return source,inv

    def test_weekday_literal_reaches_verifier_without_repair(self):
        src, inv=self.date_fixture('Monday, July 13, 2026','2026-07-13')
        out=p.assemble(src,inv)
        self.assertTrue(out['validation']['valid'],out['validation']['errors'])
        common=p.verification_payload(src,out)
        self.assertEqual(common['payload']['record']['events'][0]['timing'][0]['raw'],'Monday, July 13, 2026')
        for raw,value in [('July 13, 2026','2026-07-14'),('February 29, 2026','2026-02-29'),('Tues July 13, 2026','2026-07-13'),('Tuesday July 13, 2026','2026-07-13'),('July 13','2026-07-13'),('February 30, 2026','2026-02-30'),('07/13/2026','2026-07-13'),('July 13, 2026 at 10 AM','2026-07-13')]:
            s,i=self.date_fixture(raw,value)
            self.assertFalse(p.assemble(s,i)['validation']['valid'],raw)

    def test_multiline_components_and_new_verdict_ids(self):
        src=p.make_source('Hearing at Office.\n10 Main St.\nCity. Present orally.', 'component-control')
        inv=f.empty_inventory(src)
        inv['events']=[f.event('hearing','hearing','Hearing at Office.')]
        inv['routes']=[dict(id='venue',channel='in_person',role='other',components=[
            dict(id='office',kind='name',literal='Office',evidence=f.evidence('Office')),
            dict(id='street',kind='address_part',literal='10 Main St.',evidence=f.evidence('10 Main St.')),
            dict(id='city',kind='address_part',literal='City.',evidence=f.evidence('City.'))],
            description='Hearing venue',event_ids=['hearing'],alternative_group_id=None,association='source_resolved',evidence=f.evidence(src['source_text']))]
        out=p.assemble(src,inv)
        self.assertTrue(out['validation']['valid'],out['validation']['errors'])
        self.assertEqual({i['id'] for _,i in p.all_items(out['record'])},{'hearing','venue','office','street','city'})
        p.verification_payload(src,out)
        for change in ('invented','ambiguous','display','duplicate'):
            bad=copy.deepcopy(inv)
            if change=='invented':bad['routes'][0]['components'][0]['literal']='Imaginary Office'
            if change=='ambiguous':bad['routes'][0]['components'][0]['evidence']=f.evidence('.')
            if change=='display':bad['routes'][0]['display']='Office; unsupported endpoint'
            if change=='duplicate':bad['routes'][0]['components'][0]['id']='hearing'
            self.assertFalse(p.assemble(src,bad)['validation']['valid'],change)

    def test_help_alternatives_preserve_roles_and_qualifications(self):
        src=p.make_source('Hearing. For help call 555 or via email a@b.org. Dial-in is audio only.', 'group-control')
        inv=f.empty_inventory(src);inv['events']=[f.event('hearing','hearing','Hearing.')]
        inv['routes']=[f.route('phone','555','555',['hearing'],'help',role='information_contact',channel='telephone'),f.route('email','a@b.org','a@b.org',['hearing'],'help',role='information_contact')]
        inv['requirements']=[f.requirement('scope','other','Dial-in is audio only.',['hearing'],['phone'])]
        inv['alternative_groups']=[dict(id='help',purpose='hearing_help',route_ids=['phone','email'],event_ids=['hearing'],requirement_ids=['scope'],association='source_resolved',evidence=f.evidence('For help call 555 or via email a@b.org.'))]
        out=p.assemble(src,inv);self.assertTrue(out['validation']['valid'],out['validation']['errors'])
        self.assertEqual(out['record']['routes'][0]['role'],'information_contact')
        self.assertIn('help',{i['id'] for _,i in p.all_items(out['record'])})
        for change in ('role','scope','reciprocal','singleton','evidence'):
            bad=copy.deepcopy(inv)
            if change=='role':bad['routes'][0]['role']='submission'
            if change=='scope':bad['routes'][0]['event_ids']=[]
            if change=='reciprocal':bad['routes'][0]['alternative_group_id']=None
            if change=='singleton':bad['alternative_groups'][0]['route_ids']=['phone']
            if change=='evidence':bad['alternative_groups'][0]['evidence']=[]
            self.assertFalse(p.assemble(src,bad)['validation']['valid'],change)
        uncertain=copy.deepcopy(inv);uncertain['alternative_groups'][0]['association']='uncertain'
        out=p.assemble(src,uncertain);self.assertTrue(out['validation']['valid']);self.assertIn('association_unresolved',out['validation']['review_reasons'])

    def test_verdict_covers_components_and_caller_mutation_fails(self):
        src,inv=self.date_fixture('July 13, 2026','2026-07-13')
        inv['routes']=[f.route('oral','Comments','Comments',['comment'],channel='oral')]
        out=p.assemble(src,inv);self.assertTrue(out['validation']['valid'])
        good=f.verdict(src,out);self.assertTrue(p.validate_verdict(src,out,good)['valid'])
        for change in ('missing','duplicate','payload','quote','document','contradiction'):
            bad=copy.deepcopy(good)
            if change=='missing':bad['assessments'].pop()
            if change=='duplicate':bad['assessments'].append(copy.deepcopy(bad['assessments'][0]))
            if change=='payload':bad['payload_sha256']='0'*64
            if change=='quote':bad['assessments'][0]['evidence']=f.evidence('absent text')
            if change=='document':bad['document_id']='wrong'
            if change=='contradiction':bad['missing_items']=[dict(kind='component',description='missing',evidence=f.evidence('Comments'))]
            self.assertFalse(p.validate_verdict(src,out,bad)['valid'],change)
        bad=copy.deepcopy(out);bad['record']['routes'][0]['components'][0]['literal']='altered'
        with self.assertRaises(ValueError):p.verification_payload(src,bad)
        for occurrence,context in [(None,None),(1,'July 13, 2026.'),(2,'Comments close July 13, 2026.')]:
            repeated=p.make_source('Comments close July 13, 2026. July 13, 2026.','repeat')
            candidate=f.empty_inventory(repeated);candidate['events']=[f.event('event','written_comment','Comments close July 13, 2026.',[f.timing('time','July 13, 2026','2026-07-13')])]
            candidate['events'][0]['timing'][0]['evidence']=f.evidence('July 13, 2026',occurrence,context)
            self.assertFalse(p.assemble(repeated,candidate)['validation']['valid'])

    def test_observed_weekdays_and_exact_source_identity_caps(self):
        for raw,value in [('Monday July 13, 2026','2026-07-13'),('Friday July 10, 2026','2026-07-10'),('Monday October 5, 2026','2026-10-05'),('Fri., October 2, 2026','2026-10-02'),('2026-07-13','2026-07-13')]:
            src,inv=self.date_fixture(raw,value);self.assertTrue(p.assemble(src,inv)['validation']['valid'])
        src,inv=self.date_fixture('July 13, 2026','2026-07-13')
        for change in ('source_hash','inventory_hash','document','old_version','aggregate'):
            source=copy.deepcopy(src);bad=copy.deepcopy(inv)
            if change=='source_hash':source['source_text_sha256']='0'*64
            if change=='inventory_hash':bad['source_text_sha256']='0'*64
            if change=='document':bad['document_id']='another'
            if change=='old_version':bad['schema_version']='round6.source_inventory.v1'
            if change=='aggregate':
                bad['routes']=[f.route('route'+str(i),'Comments','Comments',['comment']) for i in range(100)]
            self.assertFalse(p.assemble(source,bad)['validation']['valid'],change)
        conflict,_=self.date_fixture('Tuesday July 13, 2026','2026-07-13')
        conflict_inv=f.empty_inventory(conflict);conflict_inv['events']=[f.event('comment','written_comment',conflict['source_text'],[f.timing('close','Tuesday July 13, 2026','2026-07-13')])]
        self.assertIn('printed weekday/date inconsistent',';'.join(p.assemble(conflict,conflict_inv)['validation']['errors']))

if __name__=='__main__': unittest.main(verbosity=2)
