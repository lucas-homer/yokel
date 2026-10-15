INTERVAL=['26-11','26-12','26-13','26-14','26-15','26-16']
BACKWARD=['25-23','25-24']+[f'26-{i:02d}' for i in range(1,11)]
FOLLOW=['26-17','26-18','26-19']
FUTURE=['26-20','26-21']
TYPES=['PREP','PROP','EXPE','PERM','EMER','MISC']
BACK_TYPES=['PREP','PROP','EXPE']
FOLLOW_TYPES=['PROP','EXPE','MISC']
PDF_SECTIONS=TYPES+['TABLE','INDEX']
B='https://lawfilesext.leg.wa.gov/law'
def ydir(iss):
    y,i=iss.split('-'); return f'20{y}/{i}'
def type_index_url(iss,t): return f'{B}/wsr/{ydir(iss)}/WSR{iss}{t}.htm'
def type_pdf_url(iss,t): return f'{B}/wsr/{ydir(iss)}/{iss}{t}.pdf'
def filing_htm(w):
    y,i,_=w.split('-'); return f'{B}/wsr/20{y}/{i}/{w}.htm'
def filing_pdf(w):
    y,i,_=w.split('-'); return f'{B}/wsrpdf/20{y}/{i}/{w}.pdf'
