import datetime
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet

def generate_pdf(   form_name:str, 
                    data_structure, 
                    username, 
                    document_name=None, 
                    encrypt=None):

    # if the user doesn't pass their own document name, create one
    if not document_name: 
        document_name= f'{datetime.datetime.utcnow().strftime("%Y-%m-%d")}_{username}_{form_name}.pdf'


    doc = SimpleDocTemplate(document_name, pagesize=letter, rightMargin=30,
                            leftMargin=30, topMargin=30, bottomMargin=18)
    
    elements = []

    data = []

    for key, value in data_structure.items():
        if key != 'Journal':
            data.append([key.replace('_'," "), str(value)])
    
    print(data)

    # # https://stackoverflow.com/questions/3372885/how-to-make-a-simple-table-in-reportlab
    # table = Table(data, colWidths=270, rowHeights=79)
    # elements.append(table)
    # doc.build(elements) 
    
    # # https://zewaren.net/reportlab.html
    style = TableStyle([('ALIGN',(1,1),(-2,-2),'RIGHT'),
                       ('TEXTCOLOR',(1,1),(-2,-2),colors.red),
                       ('VALIGN',(0,0),(0,-1),'TOP'),
                       ('TEXTCOLOR',(0,0),(0,-1),colors.blue),
                       ('ALIGN',(0,-1),(-1,-1),'CENTER'),
                       ('VALIGN',(0,-1),(-1,-1),'MIDDLE'),
                       ('TEXTCOLOR',(0,-1),(-1,-1),colors.green),
                       ('INNERGRID', (0,0), (-1,-1), 0.25, colors.black),
                       ('BOX', (0,0), (-1,-1), 0.25, colors.black),
                       ])

    # #Configure style and word wrap
    s = getSampleStyleSheet()
    s = s["BodyText"]
    s.wordWrap = 'CJK'
    data2 = [[Paragraph(cell, s) for cell in row] for row in data]
    t=Table(data2)
    t.setStyle(style)

    # #Send the data and build the file
    elements.append(t)
    doc.build(elements)



if __name__=="__main__":
    data = {'Description': 'This project requests approval for $3 million over seven '
                'years to develop a turnip GMO with significantly increased '
                'nutritional value.',
            'Existing_Request': 'No',
            'Job_Number': '23854',
            'Mission_Team': 'Special Projects (SP)',
            'Owner': 'John Smith (smithj22@example.com)',
            'Reporter': 'smithj22',
            'Risk_Level': 'medium',
            'Select': ['1'],
            'Shortname': 'Nutritional Value of Turnips',
            'Start_Date': '2022-12-29',
            'Timestamp': '2022-11-27 15:03:00.949681',
            '_id': '63837c241cc1c836267a4c24'}
    
    print (data)
    
    generate_pdf('status', data, '')