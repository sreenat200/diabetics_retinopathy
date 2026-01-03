import os
import csv
import json
from datetime import datetime
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, KeepTogether
from reportlab.lib import colors
from reportlab.graphics.shapes import Drawing, Group, Circle, Rect, Ellipse
from config import Config

class ReportGenerator:
    """Generate professional medical PDF reports with RetinaAI branding"""
    
    def __init__(self):
        self.report_folder = Config.REPORT_FOLDER
        self.timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Brand Colors (Professional Medical Indigo/Slate Theme)
        self.brand_primary = colors.HexColor('#4f46e5')  # Indigo 600
        self.brand_secondary = colors.HexColor('#4338ca') # Indigo 700
        self.brand_accent = colors.HexColor('#e0f2fe')    # Light Blue 100
        self.text_primary = colors.HexColor('#1e293b')    # Slate 800
        self.text_secondary = colors.HexColor('#64748b')  # Slate 500
        self.border_color = colors.HexColor('#e2e8f0')    # Slate 200
        self.bg_light = colors.HexColor('#f8fafc')        # Slate 50
    
    def _create_styles(self):
        """Create custom paragraph styles matching the web interface"""
        styles = getSampleStyleSheet()
        
        # Main Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=22,
            fontName='Helvetica-Bold',
            textColor=self.text_primary,
            spaceAfter=4,
            alignment=0,  # Left aligned for letterhead style
            leading=26
        )
        
        # Header Meta (Date/ID)
        header_meta_style = ParagraphStyle(
            'HeaderMeta',
            parent=styles['Normal'],
            fontSize=9,
            textColor=self.text_secondary,
            alignment=2,  # Right aligned
            fontName='Helvetica'
        )
        
        # Section Heading - Clinical Indigo
        section_heading = ParagraphStyle(
            'SectionHeading',
            parent=styles['Heading2'],
            fontSize=11,
            fontName='Helvetica-Bold',
            textColor=self.brand_primary,
            spaceAfter=8,
            spaceBefore=16,
            leading=14,
            alignment=0,
            textTransform='uppercase'
        )
        
        # Labels
        label_style = ParagraphStyle(
            'Label',
            parent=styles['Normal'],
            fontSize=9,
            fontName='Helvetica-Bold',
            textColor=self.text_secondary,
            spaceAfter=2,
            alignment=0
        )
        
        # Values
        value_style = ParagraphStyle(
            'Value',
            parent=styles['Normal'],
            fontSize=10,
            fontName='Helvetica',
            textColor=self.text_primary,
            spaceAfter=2,
            alignment=0
        )
        
        # Conclusion Box Text
        conclusion_body = ParagraphStyle(
            'ConclusionBody',
            parent=styles['Normal'],
            fontSize=10,
            fontName='Helvetica-Bold',
            textColor=self.text_primary,
            leading=15,
            alignment=0
        )
        
        # Footer
        footer_style = ParagraphStyle(
            'Footer',
            parent=styles['Normal'],
            fontSize=7,
            textColor=self.text_secondary,
            spaceAfter=0,
            leading=9,
            alignment=1
        )
        
        return {
            'title': title_style,
            'header_meta': header_meta_style,
            'section_heading': section_heading,
            'label': label_style,
            'value': value_style,
            'conclusion_body': conclusion_body,
            'footer': footer_style,
            'normal': styles['Normal']
        }

    def _get_retina_ai_logo(self):
        """Generates a robust vector graphic of the RetinaAI logo (Eye Icon)."""
        try:
            # Canvas 32x32
            d = Drawing(32, 32)
            # 1. Background: Rounded Rect (Indigo Gradient Simulation)
            bg = Rect(0, 0, 32, 32, rx=6, ry=6)
            bg.fillColor = self.brand_primary
            bg.strokeColor = None
            d.add(bg)
            # 2. Eye Outline (Sclera)
            eye = Ellipse(16, 16, 10, 6)
            eye.fillColor = None # Transparent fill
            eye.strokeColor = colors.white
            eye.strokeWidth = 1.5
            d.add(eye)
            # 3. Pupil
            pupil = Circle(16, 16, 3)
            pupil.fillColor = None
            pupil.strokeColor = colors.white
            pupil.strokeWidth = 1.5
            d.add(pupil)
            return d
        except Exception as e:
            print(f"Logo generation warning: {e}")
            return None

    def _get_conclusion_text(self, class_name):
        conclusions = {
            'No DR': 'No signs of diabetic retinopathy. Routine annual screening is advised.',
            'Mild': 'Mild diabetic retinopathy detected. Regular monitoring and good diabetic control are recommended.',
            'Moderate': 'Moderate DR detected. Further ophthalmic evaluation is advised.',
            'Severe': 'Severe DR detected. Immediate ophthalmologist consultation is recommended.',
            'Proliferative': 'Proliferative DR detected. Urgent specialist treatment is required.'
        }
        return conclusions.get(class_name, 'Clinical evaluation recommended.')

    def _get_severity_color(self, class_name):
        colors_map = {
            'No DR': colors.HexColor('#059669'),      # Emerald 600
            'Mild': colors.HexColor('#0284c7'),       # Sky 600
            'Moderate': colors.HexColor('#d97706'),   # Amber 600
            'Severe': colors.HexColor('#dc2626'),     # Red 600
            'Proliferative': colors.HexColor('#7f1d1d') # Red 900
        }
        return colors_map.get(class_name, colors.black)

    def generate_batch_pdf_report(self, diagnoses, patient, doctor, output_filename=None, use_memory=True):
        try:
            if use_memory:
                output_target = BytesIO()
            else:
                if output_filename is None:
                    output_filename = f"batch_report_{patient.id}_{self.timestamp}.pdf"
                output_target = os.path.join(self.report_folder, output_filename)
            
            doc = SimpleDocTemplate(output_target, pagesize=letter, 
                                  topMargin=0.5*inch, bottomMargin=0.5*inch, 
                                  leftMargin=0.75*inch, rightMargin=0.75*inch)
            story = []
            styles = self._create_styles()
            
            # ==================== HEADER ====================
            logo_drawing = self._get_retina_ai_logo()
            logo_cell = logo_drawing if logo_drawing else ""
            
            brand_name = Paragraph("RetinaAI", ParagraphStyle('Brand', parent=styles['normal'], fontSize=16, fontName='Helvetica-Bold', textColor=self.text_primary, spaceBefore=6))
            doc_title = Paragraph("DIAGNOSTIC REPORT", ParagraphStyle('DocTitle', parent=styles['normal'], fontSize=10, fontName='Helvetica', textColor=self.text_secondary, spaceBefore=6))

            header_data = [[
                logo_cell, 
                [brand_name, doc_title],
                "",
                [Paragraph(f"<b>DATE:</b> {datetime.now().strftime('%b %d, %Y')}", styles['header_meta'])]
            ]]
            
            header_table = Table(header_data, colWidths=[0.6*inch, 2.5*inch, 1.4*inch, 2.5*inch])
            header_table.setStyle(TableStyle([
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('LEFTPADDING', (0,0), (0,0), 0),
                ('RIGHTPADDING', (-1,0), (-1,0), 0),
            ]))
            story.append(header_table)
            
            story.append(Spacer(1, 0.15*inch))
            story.append(Table([['']], colWidths=[7*inch], style=[('LINEBELOW', (0,0), (-1,-1), 1.5, self.brand_primary)]))
            story.append(Spacer(1, 0.2*inch))
            
            # ==================== PATIENT & PHYSICIAN GRID ====================
            story.append(Paragraph("PATIENT & PHYSICIAN DETAILS", styles['section_heading']))
            
            p_details = [
                [Paragraph("Patient Name", styles['label']), Paragraph(f"{patient.first_name} {patient.last_name}", styles['value'])],
                [Paragraph("Medical ID", styles['label']), Paragraph(f"{patient.medical_id if patient.medical_id else f'PID-{patient.id}'}", styles['value'])],
                [Paragraph("Age / Gender", styles['label']), Paragraph(f"{patient.age if patient.age else 'N/A'} / {patient.gender if patient.gender else 'N/A'}", styles['value'])],
                [Paragraph("Contact", styles['label']), Paragraph(f"{patient.phone if patient.phone else 'N/A'}", styles['value'])]
            ]
            
            d_details = [
                [Paragraph("Physician", styles['label']), Paragraph(f"Dr. {doctor.first_name} {doctor.last_name}", styles['value'])],
                [Paragraph("Hospital", styles['label']), Paragraph(f"{doctor.hospital_name if hasattr(doctor, 'hospital_name') and doctor.hospital_name else 'N/A'}", styles['value'])],
                [Paragraph("Email", styles['label']), Paragraph(f"{doctor.email}", styles['value'])],
                [Paragraph("", styles['label']), Paragraph("", styles['value'])]
            ]
            
            t_patient = Table(p_details, colWidths=[1.1*inch, 2.2*inch])
            t_doctor = Table(d_details, colWidths=[1.1*inch, 2.2*inch])
            
            sub_table_style = TableStyle([
                ('VALIGN', (0,0), (-1,-1), 'TOP'),
                ('LINEBELOW', (0,0), (-1,-1), 0.5, self.border_color),
                ('PADDING', (0,0), (-1,-1), 6),
            ])
            t_patient.setStyle(sub_table_style)
            t_doctor.setStyle(sub_table_style)
            
            master_table = Table([[t_patient, "", t_doctor]], colWidths=[3.4*inch, 0.2*inch, 3.4*inch])
            master_table.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP')]))
            story.append(master_table)
            
            # ==================== SUMMARY STATS ====================
            story.append(Spacer(1, 0.1*inch))
            story.append(Paragraph("ANALYSIS SUMMARY", styles['section_heading']))
            
            successful = sum(1 for d in diagnoses if d is not None)
            total = len(diagnoses)
            rate = int((successful/total)*100) if total > 0 else 0
            
            summary_header = [Paragraph("TOTAL IMAGES", styles['label']), Paragraph("ANALYZED", styles['label']), Paragraph("CONFIDENCE", styles['label'])]
            summary_values = [
                Paragraph(str(total), ParagraphStyle('BigVal', parent=styles['value'], fontSize=12, fontName='Helvetica-Bold')),
                Paragraph(str(successful), ParagraphStyle('BigVal', parent=styles['value'], fontSize=12, fontName='Helvetica-Bold')),
                Paragraph(f"{rate}%", ParagraphStyle('BigVal', parent=styles['value'], fontSize=12, fontName='Helvetica-Bold', textColor=self.brand_primary))
            ]
            
            summary_table = Table([summary_header, summary_values], colWidths=[2.3*inch, 2.3*inch, 2.3*inch])
            summary_table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,-1), self.bg_light),
                ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                ('PADDING', (0,0), (-1,-1), 10),
                ('GRID', (0,0), (-1,-1), 1, colors.white)
            ]))
            story.append(summary_table)
            
            # ==================== DETAILED RESULTS ====================
            story.append(Spacer(1, 0.1*inch))
            story.append(Paragraph("DETAILED FINDINGS", styles['section_heading']))
            
            results_data = [[
                Paragraph("IMAGE ID", styles['label']),
                Paragraph("CLASSIFICATION", styles['label']),
                Paragraph("CONFIDENCE", styles['label'])
            ]]
            
            for idx, diagnosis in enumerate(diagnoses, 1):
                if diagnosis:
                    sev_color = self._get_severity_color(diagnosis.class_name)
                    class_text = f"<font color='{sev_color.hexval()}'><b>{diagnosis.class_name}</b></font>"
                    results_data.append([
                        Paragraph(f"IMG-{idx:03d}", styles['value']),
                        Paragraph(class_text, styles['value']),
                        Paragraph(f"{diagnosis.confidence_percent:.1f}%", styles['value'])
                    ])
            
            results_table = Table(results_data, colWidths=[2*inch, 3*inch, 2*inch])
            results_table.setStyle(TableStyle([
                ('LINEBELOW', (0,0), (-1,0), 1, self.brand_primary),
                ('LINEBELOW', (0,1), (-1,-1), 0.5, self.border_color),
                ('PADDING', (0,0), (-1,-1), 8),
                ('BACKGROUND', (0,0), (-1,0), self.bg_light),
            ]))
            story.append(results_table)
            
            # ==================== CONCLUSION ====================
            overall_class = None
            class_priority = {'Proliferative': 4, 'Severe': 3, 'Moderate': 2, 'Mild': 1, 'No DR': 0}
            max_priority = -1
            for d in diagnoses:
                if d:
                    priority = class_priority.get(d.class_name, -1)
                    if priority > max_priority:
                        max_priority = priority
                        overall_class = d.class_name
            
            if overall_class:
                story.append(Spacer(1, 0.2*inch))
                story.append(Paragraph("FINAL CONCLUSION", styles['section_heading']))
                conclusion_text = self._get_conclusion_text(overall_class)
                c_table = Table([[Paragraph(conclusion_text, styles['conclusion_body'])]], colWidths=[7*inch])
                c_table.setStyle(TableStyle([
                    ('BACKGROUND', (0,0), (-1,-1), self.brand_accent),
                    ('BORDER', (0,0), (-1,-1), 1, self.brand_primary),
                    ('PADDING', (0,0), (-1,-1), 12),
                ]))
                story.append(c_table)

            # ==================== CLINICAL OBSERVATIONS ====================
            clinical_observations = []
            seen_observations = set()
            for diagnosis in diagnoses:
                if hasattr(diagnosis, 'notes') and diagnosis.notes:
                    note = diagnosis.notes.strip()
                    if note and note not in seen_observations:
                        clinical_observations.append(note)
                        seen_observations.add(note)
            
            if clinical_observations:
                story.append(Spacer(1, 0.2*inch))
                story.append(Paragraph("CLINICAL OBSERVATIONS", styles['section_heading']))
                combined_notes = "<br/><br/>".join(clinical_observations)
                notes_table = Table([[Paragraph(combined_notes, styles['value'])]], colWidths=[7*inch])
                notes_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, -1), self.bg_light),
                    ('BORDER', (0, 0), (-1, -1), 0.5, self.border_color),
                    ('PADDING', (0, 0), (-1, -1), 10)
                ]))
                story.append(notes_table)

            # ==================== FOOTER ====================
            story.append(Spacer(1, 0.4*inch))
            story.append(Table([['']], colWidths=[7*inch], style=[('LINEABOVE', (0,0), (-1,-1), 0.5, self.border_color)]))
            story.append(Spacer(1, 0.05*inch))
            footer_text = f"RetinaAI Diagnostics | Dr. {doctor.first_name} {doctor.last_name} | {doctor.email}<br/>DISCLAIMER: This report is computer-generated and is for reference only. Clinical correlation is required."
            story.append(Paragraph(footer_text, styles['footer']))
            
            doc.build(story)
            if use_memory:
                output_target.seek(0)
                return output_target
            return output_target
            
        except Exception as e:
            print(f"Error generating batch report: {str(e)}")
            return None

    def generate_batch_history_pdf_report(self, diagnoses, patient, doctor, output_filename=None, use_memory=True):
        """Generate a branded history report with Patient & Physician Info and Clinical Observations"""
        try:
            if use_memory:
                output_target = BytesIO()
            else:
                if output_filename is None:
                    output_filename = f"history_report_{patient.id}_{self.timestamp}.pdf"
                output_target = os.path.join(self.report_folder, output_filename)
            
            doc = SimpleDocTemplate(output_target, pagesize=letter, 
                                  topMargin=0.5*inch, bottomMargin=0.5*inch, 
                                  leftMargin=0.75*inch, rightMargin=0.75*inch)
            story = []
            styles = self._create_styles()
            
            # Header
            logo_drawing = self._get_retina_ai_logo()
            logo_cell = logo_drawing if logo_drawing else ""
            
            brand_name = Paragraph("RetinaAI", ParagraphStyle('Brand', parent=styles['normal'], fontSize=16, fontName='Helvetica-Bold', textColor=self.text_primary, spaceBefore=6))
            doc_title = Paragraph("PATIENT HISTORY REPORT", ParagraphStyle('Sub', parent=styles['normal'], fontSize=10, textColor=self.text_secondary, spaceBefore=6))
            
            header_data = [[logo_cell, [brand_name, doc_title], "", [Paragraph(f"<b>DATE:</b> {datetime.now().strftime('%b %d, %Y')}", styles['header_meta'])]]]
            header_table = Table(header_data, colWidths=[0.6*inch, 2.5*inch, 1.4*inch, 2.5*inch])
            header_table.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'MIDDLE')]))
            story.append(header_table)
            
            story.append(Spacer(1, 0.15*inch))
            story.append(Table([['']], colWidths=[7*inch], style=[('LINEBELOW', (0,0), (-1,-1), 1.5, self.brand_primary)]))
            story.append(Spacer(1, 0.2*inch))
            
            # ==================== PATIENT & PHYSICIAN DETAILS ====================
            story.append(Paragraph("PATIENT & PHYSICIAN DETAILS", styles['section_heading']))
            
            p_details = [
                [Paragraph("Patient Name", styles['label']), Paragraph(f"{patient.first_name} {patient.last_name}", styles['value'])],
                [Paragraph("Medical ID", styles['label']), Paragraph(f"{patient.medical_id if patient.medical_id else f'PID-{patient.id}'}", styles['value'])],
                [Paragraph("Age / Gender", styles['label']), Paragraph(f"{patient.age if patient.age else 'N/A'} / {patient.gender if patient.gender else 'N/A'}", styles['value'])],
                [Paragraph("Contact", styles['label']), Paragraph(f"{patient.phone if patient.phone else 'N/A'}", styles['value'])]
            ]
            
            d_details = [
                [Paragraph("Physician", styles['label']), Paragraph(f"Dr. {doctor.first_name} {doctor.last_name}", styles['value'])],
                [Paragraph("Hospital", styles['label']), Paragraph(f"{doctor.hospital_name if hasattr(doctor, 'hospital_name') and doctor.hospital_name else 'N/A'}", styles['value'])],
                [Paragraph("Email", styles['label']), Paragraph(f"{doctor.email}", styles['value'])],
                [Paragraph("", styles['label']), Paragraph("", styles['value'])]
            ]
            
            t_patient = Table(p_details, colWidths=[1.1*inch, 2.2*inch])
            t_doctor = Table(d_details, colWidths=[1.1*inch, 2.2*inch])
            
            sub_table_style = TableStyle([
                ('VALIGN', (0,0), (-1,-1), 'TOP'),
                ('LINEBELOW', (0,0), (-1,-1), 0.5, self.border_color),
                ('PADDING', (0,0), (-1,-1), 6),
            ])
            t_patient.setStyle(sub_table_style)
            t_doctor.setStyle(sub_table_style)
            
            master_table = Table([[t_patient, "", t_doctor]], colWidths=[3.4*inch, 0.2*inch, 3.4*inch])
            master_table.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP')]))
            story.append(master_table)
            
            # History Table
            story.append(Spacer(1, 0.2*inch))
            story.append(Paragraph("DIAGNOSIS HISTORY", styles['section_heading']))
            
            history_by_date = {}
            for d in diagnoses:
                dk = d.created_at.strftime('%Y-%m-%d %I:%M %p')
                if dk not in history_by_date: history_by_date[dk] = []
                history_by_date[dk].append(d.class_name)
            
            h_data = [[Paragraph("DATE & TIME", styles['label']), Paragraph("FINDINGS", styles['label'])]]
            for dk in sorted(history_by_date.keys(), reverse=True):
                classes = ", ".join(sorted(set(history_by_date[dk])))
                h_data.append([Paragraph(dk, styles['value']), Paragraph(classes, styles['value'])])
            
            h_table = Table(h_data, colWidths=[2.5*inch, 4.5*inch])
            h_table.setStyle(TableStyle([
                ('LINEBELOW', (0,0), (-1,0), 1, self.brand_primary),
                ('LINEBELOW', (0,1), (-1,-1), 0.5, self.border_color),
                ('BACKGROUND', (0,0), (-1,0), self.bg_light),
                ('PADDING', (0,0), (-1,-1), 8)
            ]))
            story.append(h_table)
            
            # ==================== CLINICAL OBSERVATIONS ====================
            clinical_observations = []
            seen_observations = set()
            for diagnosis in diagnoses:
                if hasattr(diagnosis, 'notes') and diagnosis.notes:
                    note = diagnosis.notes.strip()
                    if note and note not in seen_observations:
                        clinical_observations.append(note)
                        seen_observations.add(note)
            
            if clinical_observations:
                story.append(Spacer(1, 0.2*inch))
                story.append(Paragraph("CLINICAL OBSERVATIONS", styles['section_heading']))
                combined_notes = "<br/><br/>".join(clinical_observations)
                notes_table = Table([[Paragraph(combined_notes, styles['value'])]], colWidths=[7*inch])
                notes_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, -1), self.bg_light),
                    ('BORDER', (0, 0), (-1, -1), 0.5, self.border_color),
                    ('PADDING', (0, 0), (-1, -1), 10)
                ]))
                story.append(notes_table)
            
            # Footer
            story.append(Spacer(1, 0.4*inch))
            story.append(Table([['']], colWidths=[7*inch], style=[('LINEABOVE', (0,0), (-1,-1), 0.5, self.border_color)]))
            story.append(Paragraph("RetinaAI | Confidential Medical Record", styles['footer']))
            
            doc.build(story)
            if use_memory:
                output_target.seek(0)
                return output_target
            return output_target
            
        except Exception as e:
            print(f"Error generating history report: {str(e)}")
            return None