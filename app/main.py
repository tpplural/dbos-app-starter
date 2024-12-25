import os
import time

from dbos import DBOS, SetWorkflowID
from fastapi import FastAPI, Form, Request, Depends
from fastapi.responses import HTMLResponse, FileResponse, RedirectResponse
import os
from fpdf import FPDF
from datetime import datetime

# Welcome to DBOS!
# This is a template application built with DBOS and FastAPI.
# It shows you how to use DBOS to build background tasks that are resilient to any failure.


class DorosliPDF(FPDF):
    def __init__(self, title, prowadzacy, date):
        super().__init__()
        self.title = title
        self.date = date
        self.prowadzacy = prowadzacy


    def header(self):
        # Add header image
        self.image('kolektyw2.png', 10, 3, 33)  # Adjust position and size as needed
        
        #add header conent
        self.set_font('DejaVu', '', 8)
        self.set_xy(10, 10)
        header_text = """Lista obecności na zajęciach stowarzyszenia Kolektyw Pomysłów\nw ramach zadania publicznego\nCENTRA AKTYWNOŚCI LOKALNEJ WE WROCŁAWIU"""
        self.multi_cell(0, 6, header_text, 0, align='C')
        #drugie logo
        self.image('cal.png', 160, 1, 33)  # x=140, y=8, width=33
        # Add the title
        self.ln(10)
        self.set_font('DejaVu', '', 16)
        self.cell(0, 10, "Zajęcia: " + str(self.title), ln=True, align='L')
        # Add the date
        #self.set_font('Arial', '', 12)
        #self.cell(0, 10, "Prowadzacy: " + self.date, ln=True, align='L')
        self.set_font('DejaVu', '', 12)
        self.cell(0, 7, "Prowadzący: " + str(self.prowadzacy), ln=True, align='L')
        self.cell(0, 7, "Data: " + str(self.date), ln=True, align='L')
        self.ln(5)  # Add some vertical space after the header
        DBOS.logger.info("---------------------------header created")


    def footer(self):
        # Add footer image if provided
        self.set_xy(5, -19)  # Position 20mm from the bottom
        self.image('wroclaw_footer.png', w = 50)  # Adjust position and size as needed
       
        # Add the footer static text
        self.set_y(-20)  # Position 20mm from the bottom
        self.set_font('DejaVu', '', 8)
        footer_text = """Projekt „CENTRA AKTYWNOŚCI LOKALNEJ WE WROCŁAWIU"\nwspółfinansowany jest ze środków Gminy Wrocław, www.wroclaw.pl"""
        regulamin_text = """Udział w zajęciach oznacza zgodę na regulamin CAL:https://suwalska11.pl/wp-content/uploads/2024/10/regulamin_zajec-1.pdf"""
        self.multi_cell(0, 5, footer_text, align='C')
        self.set_font('DejaVu', '', 5)
        self.ln(3)
        self.multi_cell(0, 5, regulamin_text, align='R')
        DBOS.logger.info("---------------------------footer created")

app = FastAPI()
DBOS(fastapi=app)

steps_event = "steps_event"

# This endpoint uses DBOS to idempotently launch a crashproof background task with N steps.

def generate_pdf_filename(data: str, name: str) -> str:
    # Use current date if 'data' is empty
    if not data:
        data = datetime.now().strftime("%Y.%m.%d")
    
    # Format the filename
    if name:
        filename = f"{data}_{name}_lista_dorosli.pdf"
    else:
        filename = f"{data}_lista_dorosli.pdf"
    
    return filename

def sanitize_input(input_data):
    if isinstance(input_data, bytes):  # Check if input is bytes
        input_data = input_data.decode('utf-8', errors='replace')  # Decode to string
    return input_data.encode('utf-8', errors='replace').decode('utf-8')  # Re-encode and decode to ensure UTF-8

@app.get("/background/{task_id}/{n}")
def launch_background_task(task_id: str, n: int) -> None:
    with SetWorkflowID(task_id):
        DBOS.start_workflow(background_task, n)


# This workflow simulates a background task with N steps.

# DBOS workflows are resilient to any failure--if your program is crashed,
# interrupted, or restarted while running this workflow, the workflow automatically
# resumes from the last completed step.


@DBOS.workflow()
def background_task(n: int) -> None:
    for i in range(1, n + 1):
        background_task_step(i)
        DBOS.set_event(steps_event, i)


@DBOS.step()
def background_task_step(i: int):
    time.sleep(2)
    DBOS.logger.info(f"Completed step {i}!")


# This endpoint retrieves the status of a specific background task.


@app.get("/last_step/{task_id}")
def get_last_completed_step(task_id: str):
    try:
        step = DBOS.get_event(task_id, steps_event)
    except KeyError: # If the task hasn't started yet
        return 0
    return step if step is not None else 0


@app.get("/")
def readme():
    DBOS.logger.info("--------------------------- called get")
    with open(os.path.join("html", "form.html")) as file:
        html = file.read()
    return HTMLResponse(html)

@app.post("/submit")
async def submit_form(title: str = Form(...),prowadzacy: str = Form(...),dropdown_choice: str = Form(...), data: str = Form(...),multiline_input: str = Form(...)):
    DBOS.logger.info("--------------------------- called submit")
    file_path = generate_pdf_filename(data, title) 
    if dropdown_choice == 'list1':
        DBOS.logger.info("--------------------------- first element from dropwon chosen")
        create_pdf_dorosli(title ,prowadzacy, data, multiline_input, file_path)
    else:
        DBOS.logger.info("--------------------------- some another element from dropwon chosen")
        create_pdf_dorosli(title ,prowadzacy, data, multiline_input, file_path)
    DBOS.logger.info("-------------------finished submit call")
    return FileResponse(file_path, media_type="application/pdf", filename=file_path)


def create_pdf_dorosli(title ,prowadzacy, date,multiline_input,filename):       
    DBOS.logger.info("-------------------create pdf called")
    pdf = DorosliPDF(title, prowadzacy, date)
    pdf.add_font('DejaVu', '', 'DejaVuSans.ttf', uni=True)
    pdf.add_page()
    
    # Table Header
    pdf.set_font("Arial", size=12, style="B")
    column_widths = [10, 90, 15, 15, 15, 15, 15, 15]  # Define widths for the 8 columns

    headers = ["L.P.", "Osoba", "....", "....", "....", "....", "....", "...."]
    for header, width in zip(headers, column_widths):
        pdf.cell(width, 10, header, border=1, align='C')
    pdf.ln()
    # Table Content
    pdf.set_font('DejaVu', '', 12)
    multiline_input = str(multiline_input)
    lines = multiline_input.split("\n")  # Ensure maximum of 30 lines
    for idx, line in enumerate(lines, start=1):
        pdf.cell(column_widths[0], 10, str(idx), border=1, align='C')  # Row number
        pdf.cell(column_widths[1], 10, line, border=1, align='L')  # Content line
        for width in column_widths[2:]:
            pdf.cell(width, 10, "", border=1)  # Empty columns
        pdf.ln()

    pdf.output(filename)
    DBOS.logger.info("-------------------create pdf finishing")