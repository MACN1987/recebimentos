import tkinter as tk
from tkinter import ttk, messagebox, font, simpledialog, filedialog
from calendar import monthrange
from datetime import date, timedelta
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors

# ==== Funções Auxiliares ====

def formatar(val):
    """Formata um valor numérico para o formato de moeda brasileira."""
    if val is None:
        return 'R$ 0,00'
    return f'R$ {val:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')

def count_uteis(y, m, start=1):
    """
    Conta os dias úteis em um mês, a partir de uma data de início.
    Considera de segunda a sexta.
    """
    start_date = date(y, m, start)
    end_day = monthrange(y, m)[1]
    end_date = date(y, m, end_day)
    count = 0
    current = start_date
    while current <= end_date:
        if current.weekday() < 5:  # 0 a 4 (segunda a sexta)
            count += 1
        current += timedelta(days=1)
    return count

def calc_inss(sal):
    """
    Calcula o valor do INSS com base no salário, utilizando a tabela de faixas.
    """
    INSS_FAIXAS = [
        (1518.00, 0.075, 0.00),
        (2793.88, 0.09, 22.77),
        (4190.83, 0.12, 106.59),
        (8157.41, 0.14, 190.40)
    ]
    INSS_TETO = 8157.41
    sal = min(sal, INSS_TETO)
    for faixa, pct, ded in reversed(INSS_FAIXAS):
        if sal > faixa:
            return sal * pct - ded
    return sal * INSS_FAIXAS[0][1]

def calc_irrf(base):
    """
    Calcula o valor do IRRF com base no salário, utilizando a tabela.
    """
    IRRF_TABELA = [
        (2428.80, 0.00, 0.00),
        (2826.65, 0.075, 182.16),
        (3751.05, 0.15, 394.16),
        (4664.68, 0.225, 675.49),
        (float("inf"), 0.275, 908.73)
    ]
    for faixa, pct, ded in IRRF_TABELA:
        if base <= faixa:
            return max(0, base * pct - ded)
    return 0

def val_hora(d):
    """Calcula o valor da hora de trabalho com base no valor diário."""
    return d / 8 if d else 0

def calc_h_extra(vh, h, pct):
    """Calcula o valor das horas extras."""
    return vh * h * (1 + pct / 100)

# ==== Classes Auxiliares ====

class MEIPopup(simpledialog.Dialog):
    """
    Popup para selecionar a atividade do MEI.
    """
    def body(self, master):
        self.title("Selecione atividade MEI")
        tk.Label(master, text="Escolha atividade:\n1- Comércio/Indústria\n2- Serviços\n3- Ambos").pack(padx=10, pady=10)
        self.tipo = tk.IntVar(value=1)
        options = [("1 - Comércio/Indústria", 1), ("2 - Serviços", 2), ("3 - Ambos", 3)]
        for text, val in options:
            ttk.Radiobutton(master, text=text, variable=self.tipo, value=val).pack(anchor='w', padx=20)
        return None

    def apply(self):
        self.result = self.tipo.get()

# ==== Classe Principal da Aplicação ====

class Calculadora(tk.Tk):
    def __init__(self):
        super().__init__()
        
        self.withdraw()
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        width = int(screen_width * 0.8)
        height = int(screen_height * 0.8)
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        self.geometry(f"{width}x{height}+{x}+{y}")
        self.deiconify()

        self.title("Calculadora de Pagamentos")
        self.configure(bg='#f0f0f0')
        self.resizable(True, True)

        # Variáveis de estado
        self.tipo_contrato = tk.StringVar(value='CLT')
        self.tipo_valor = tk.StringVar(value='diario')
        self.tipo_calculo = tk.StringVar(value='mes')
        self.valor = tk.StringVar()
        self.mes = tk.StringVar()
        self.ano = tk.StringVar()
        self.horas = tk.StringVar()
        self.percentual = tk.StringVar()
        self.paga_pensao = tk.IntVar()
        self.tipo_pensao = tk.StringVar(value='percent')
        self.valor_pensao = tk.StringVar()
        self.vr_fixo = tk.IntVar()
        self.valor_vr_fixo = tk.StringVar()
        self.valor_vr = tk.StringVar()
        self.va_fixo = tk.IntVar()
        self.valor_va_fixo = tk.StringVar()
        self.valor_va = tk.StringVar()
        self.vt_fixo = tk.IntVar()
        self.valor_vt_fixo = tk.StringVar()
        self.vt_percentual = tk.StringVar(value="6")
        self.atraso_horas = tk.StringVar()
        self.atraso_minutos = tk.StringVar()
        self.faltas = tk.StringVar()

        self.style = ttk.Style(self)
        self.style.configure('TButton', font=('Segoe UI', 11, 'bold'))
        self.style.configure('TRadiobutton', font=('Segoe UI', 10))
        self.style.configure('TLabel', font=('Segoe UI', 11))

        self.create_widgets()
        self.atualizar_pensao()
        self.atualizar_campos()

    def create_widgets(self):
        self.canvas = tk.Canvas(self, bg='#f0f0f0')
        self.scrollbar = ttk.Scrollbar(self, orient='vertical', command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side='left', fill='both', expand=True)
        self.scrollbar.pack(side='right', fill='y')

        self.main_frame = ttk.Frame(self.canvas, padding=15)
        self.canvas.create_window((0, 0), window=self.main_frame, anchor='nw')

        self.main_frame.bind("<Configure>", lambda event: self.canvas.configure(scrollregion=self.canvas.bbox("all")))

        cg = self.main_frame

        for i in range(25): cg.rowconfigure(i, weight=0)
        for i in range(4): cg.columnconfigure(i, weight=1)

        tt = ttk.LabelFrame(cg, text='Tipo Contrato')
        tt.grid(row=0, column=0, columnspan=4, sticky='ew', pady=5)
        opts = [('CLT', 'CLT'), ('PJ', 'PJ'), ('MEI', 'MEI')]
        for i, (t, v) in enumerate(opts):
            ttk.Radiobutton(tt, text=t, variable=self.tipo_contrato, value=v, command=self.atualizar_campos).grid(row=0, column=i, padx=10, pady=5)

        tv = ttk.LabelFrame(cg, text='Tipo Valor')
        tv.grid(row=1, column=0, columnspan=4, sticky='ew', pady=5)
        ttk.Radiobutton(tv, text='Valor Diário', variable=self.tipo_valor, value='diario').grid(row=0, column=0, padx=20, pady=5)
        ttk.Radiobutton(tv, text='Valor Total do Mês', variable=self.tipo_valor, value='total').grid(row=0, column=1, padx=20, pady=5)

        ttk.Label(cg, text='Valor (R$)').grid(row=2, column=0, sticky='e', padx=4, pady=6)
        ttk.Entry(cg, textvariable=self.valor, justify='center').grid(row=2, column=1, sticky='w', padx=4, pady=6)

        tc = ttk.LabelFrame(cg, text='Calcular para')
        tc.grid(row=3, column=0, columnspan=4, sticky='ew', pady=5)
        ttk.Radiobutton(tc, text='Mês inteiro', variable=self.tipo_calculo, value='mes').grid(row=0, column=0, padx=20, pady=5)
        ttk.Radiobutton(tc, text='A partir data específica', variable=self.tipo_calculo, value='data').grid(row=0, column=1, padx=20, pady=5)

        ttk.Label(cg, text='Mês (1-12)').grid(row=4, column=0, sticky='e', padx=4, pady=6)
        ttk.Entry(cg, textvariable=self.mes, justify='center', width=10).grid(row=4, column=1, sticky='w', padx=4, pady=6)
        ttk.Label(cg, text='Ano (ex: 2025)').grid(row=4, column=2, sticky='e', padx=4, pady=6)
        ttk.Entry(cg, textvariable=self.ano, justify='center', width=12).grid(row=4, column=3, sticky='w', padx=4, pady=6)

        self.label_horas = ttk.Label(cg, text='Horas Extras')
        self.label_horas.grid(row=5, column=0, sticky='e', padx=4, pady=6)
        self.entry_horas = ttk.Entry(cg, textvariable=self.horas, justify='center', width=12)
        self.entry_horas.grid(row=5, column=1, sticky='w', padx=4, pady=6)
        self.label_perc = ttk.Label(cg, text='Percentual (%)')
        self.label_perc.grid(row=5, column=2, sticky='e', padx=4, pady=6)
        self.entry_perc = ttk.Entry(cg, textvariable=self.percentual, justify='center', width=12)
        self.entry_perc.grid(row=5, column=3, sticky='w', padx=4, pady=6)

        self.atraso_frame = ttk.Frame(cg)
        self.atraso_frame.grid(row=6, column=0, columnspan=4, sticky='ew', pady=2)
        ttk.Label(self.atraso_frame, text='Atraso:').grid(row=0, column=0, padx=4)
        ttk.Label(self.atraso_frame, text='Horas').grid(row=0, column=1)
        ttk.Entry(self.atraso_frame, textvariable=self.atraso_horas, width=5, justify='center').grid(row=0, column=2)
        ttk.Label(self.atraso_frame, text='Minutos').grid(row=0, column=3)
        ttk.Entry(self.atraso_frame, textvariable=self.atraso_minutos, width=5, justify='center').grid(row=0, column=4)

        self.faltas_frame = ttk.Frame(cg)
        self.faltas_frame.grid(row=7, column=0, columnspan=4, sticky='ew', pady=2)
        ttk.Label(self.faltas_frame, text='Faltas (dias):').grid(row=0, column=0)
        ttk.Entry(self.faltas_frame, textvariable=self.faltas, width=6, justify='center').grid(row=0, column=1)

        self.vr_frame = ttk.LabelFrame(cg, text='Vale Refeição')
        self.vr_frame.grid(row=8, column=0, columnspan=4, sticky='ew', pady=5)
        self.chk_vr_fixo = ttk.Checkbutton(self.vr_frame, text='Desconto fixo?', variable=self.vr_fixo, command=self.toggle_vr_fixo)
        self.chk_vr_fixo.grid(row=0, column=0, padx=10, pady=8, sticky='w')
        ttk.Label(self.vr_frame, text='Desconto fixo (R$)').grid(row=0, column=1, sticky='e', padx=4, pady=6)
        self.entry_vr_fixo = ttk.Entry(self.vr_frame, textvariable=self.valor_vr_fixo, justify='center', width=12, state='disabled')
        self.entry_vr_fixo.grid(row=0, column=2, sticky='w', padx=4, pady=6)
        ttk.Label(self.vr_frame, text='Valor diário VR (R$)').grid(row=1, column=0, sticky='e', padx=4, pady=6)
        self.entry_vr = ttk.Entry(self.vr_frame, textvariable=self.valor_vr, justify='center', width=12)
        self.entry_vr.grid(row=1, column=1, sticky='w', padx=4, pady=6)

        self.va_frame = ttk.LabelFrame(cg, text='Vale Alimentação')
        self.va_frame.grid(row=9, column=0, columnspan=4, sticky='ew', pady=5)
        self.chk_va_fixo = ttk.Checkbutton(self.va_frame, text='Desconto fixo?', variable=self.va_fixo, command=self.toggle_va_fixo)
        self.chk_va_fixo.grid(row=0, column=0, padx=10, pady=8, sticky='w')
        ttk.Label(self.va_frame, text='Desconto fixo (R$)').grid(row=0, column=1, sticky='e', padx=4, pady=6)
        self.entry_va_fixo = ttk.Entry(self.va_frame, textvariable=self.valor_va_fixo, justify='center', width=12, state='disabled')
        self.entry_va_fixo.grid(row=0, column=2, sticky='w', padx=4, pady=6)
        ttk.Label(self.va_frame, text='Valor diário VA (R$)').grid(row=1, column=0, sticky='e', padx=4, pady=6)
        self.entry_va = ttk.Entry(self.va_frame, textvariable=self.valor_va, justify='center', width=12)
        self.entry_va.grid(row=1, column=1, sticky='w', padx=4, pady=6)

        self.vt_frame = ttk.LabelFrame(cg, text='Vale Transporte')
        self.vt_frame.grid(row=10, column=0, columnspan=4, sticky='ew', pady=5)
        self.chk_vt_fixo = ttk.Checkbutton(self.vt_frame, text='Desconto fixo?', variable=self.vt_fixo, command=self.toggle_vt_fixo)
        self.chk_vt_fixo.grid(row=0, column=0, padx=10, pady=8, sticky='w')
        ttk.Label(self.vt_frame, text='Desconto fixo (R$)').grid(row=0, column=1, sticky='e', padx=4, pady=6)
        self.entry_vt_fixo = ttk.Entry(self.vt_frame, textvariable=self.valor_vt_fixo, justify='center', width=12, state='disabled')
        self.entry_vt_fixo.grid(row=0, column=2, sticky='w', padx=4, pady=6)
        ttk.Label(self.vt_frame, text='Percentual (%)').grid(row=1, column=0, sticky='e', padx=4, pady=6)
        vcmd = (self.register(self.validate_vt_percent), "%P")
        self.entry_vt_percent = ttk.Entry(self.vt_frame, textvariable=self.vt_percentual, validate="key", validatecommand=vcmd, width=6)
        self.entry_vt_percent.grid(row=1, column=1, sticky='w', padx=4, pady=6)

        self.chk_pensao = ttk.Checkbutton(cg, text='Paga pensão alimentícia?', variable=self.paga_pensao, command=self.atualizar_pensao)
        self.chk_pensao.grid(row=11, column=0, columnspan=4, sticky='w')

        self.frame_pensao = ttk.Frame(cg)
        self.frame_pensao.grid(row=12, column=0, columnspan=4, sticky='ew')
        self.tipo_pensao.set('percent')
        self.radio_pct = ttk.Radiobutton(self.frame_pensao, text='Percentual (%)', variable=self.tipo_pensao, value='percent', command=self.atualizar_pensao)
        self.radio_pct.grid(row=0, column=0, padx=10, pady=5)
        self.entry_pct = ttk.Entry(self.frame_pensao, textvariable=self.valor_pensao, justify='center', width=12)
        self.entry_pct.grid(row=0, column=1, padx=10, pady=5)
        self.radio_fixo = ttk.Radiobutton(self.frame_pensao, text='Valor fixo (R$)', variable=self.tipo_pensao, value='fix', command=self.atualizar_pensao)
        self.radio_fixo.grid(row=0, column=2, padx=10, pady=5)
        self.entry_fixo = ttk.Entry(self.frame_pensao, textvariable=self.valor_pensao, justify='center', width=12)
        self.entry_fixo.grid(row=0, column=3, padx=10, pady=5)

        self.text_frame = ttk.Frame(cg)
        self.text_frame.grid(row=13, column=0, columnspan=4, sticky='nsew')
        cg.rowconfigure(13, weight=1)
        self.text = tk.Text(self.text_frame, font=('Segoe UI', 12), bg='#f0f0f0', wrap='word')
        self.text.pack(side='left', fill='both', expand=True)
        scrollbar = ttk.Scrollbar(self.text_frame, orient='vertical', command=self.text.yview)
        scrollbar.pack(side='right', fill='y')
        self.text.config(yscrollcommand=scrollbar.set)

        self.bold_font = font.Font(self.text, self.text.cget('font'))
        self.bold_font.configure(weight='bold')

        button_frame = ttk.Frame(cg)
        button_frame.grid(row=15, column=0, columnspan=4, pady=10)
        ttk.Button(button_frame, text='Calcular', command=self.calcular).grid(row=0, column=0, padx=5, sticky='ew')
        ttk.Button(button_frame, text='Limpar', command=self.limpar).grid(row=0, column=1, padx=5, sticky='ew')
        ttk.Button(button_frame, text='Sair', command=self.quit).grid(row=0, column=2, padx=5, sticky='ew')

    def validate_vt_percent(self, P):
        if P == "":
            return True
        try:
            val = float(P.replace(',', '.'))
            return 0 <= val <= 6
        except ValueError:
            return False

    def toggle_vr_fixo(self):
        if self.vr_fixo.get():
            self.entry_vr_fixo.config(state='normal')
            self.entry_vr.config(state='disabled')
        else:
            self.entry_vr_fixo.config(state='disabled')
            self.entry_vr.config(state='normal')

    def toggle_va_fixo(self):
        if self.va_fixo.get():
            self.entry_va_fixo.config(state='normal')
            self.entry_va.config(state='disabled')
        else:
            self.entry_va_fixo.config(state='disabled')
            self.entry_va.config(state='normal')

    def toggle_vt_fixo(self):
        if self.vt_fixo.get():
            self.entry_vt_fixo.config(state='normal')
            self.entry_vt_percent.config(state='disabled')
        else:
            self.entry_vt_fixo.config(state='disabled')
            self.entry_vt_percent.config(state='normal')

    def atualizar_pensao(self):
        if self.paga_pensao.get():
            self.frame_pensao.grid()
            if self.tipo_pensao.get() == 'percent':
                self.entry_pct.config(state='normal')
                self.entry_fixo.config(state='disabled')
            else:
                self.entry_pct.config(state='disabled')
                self.entry_fixo.config(state='normal')
        else:
            self.frame_pensao.grid_remove()

    def atualizar_campos(self):
        c = self.tipo_contrato.get()
        if c == 'CLT':
            self.label_horas.grid()
            self.entry_horas.grid()
            self.label_perc.grid()
            self.entry_perc.grid()
            self.atraso_frame.grid()
            self.faltas_frame.grid()
            self.vr_frame.grid()
            self.va_frame.grid()
            self.vt_frame.grid()
            self.chk_pensao.grid()
        elif c == 'PJ':
            self.label_horas.grid_remove()
            self.entry_horas.grid_remove()
            self.label_perc.grid_remove()
            self.entry_perc.grid_remove()
            self.atraso_frame.grid_remove()
            self.faltas_frame.grid_remove()
            self.vr_frame.grid_remove()
            self.va_frame.grid_remove()
            self.vt_frame.grid_remove()
            self.chk_pensao.grid()
        else: # MEI
            self.label_horas.grid_remove()
            self.entry_horas.grid_remove()
            self.label_perc.grid_remove()
            self.entry_perc.grid_remove()
            self.atraso_frame.grid_remove()
            self.faltas_frame.grid_remove()
            self.vr_frame.grid_remove()
            self.va_frame.grid_remove()
            self.vt_frame.grid_remove()
            self.chk_pensao.grid()

        self.toggle_vr_fixo()
        self.toggle_va_fixo()
        self.toggle_vt_fixo()
        self.atualizar_pensao()

    def limpar(self):
        self.tipo_contrato.set('CLT')
        self.tipo_valor.set('diario')
        self.tipo_calculo.set('mes')
        self.valor.set('')
        self.mes.set('')
        self.ano.set('')
        self.horas.set('')
        self.percentual.set('')
        self.paga_pensao.set(0)
        self.tipo_pensao.set('percent')
        self.valor_pensao.set('')
        self.valor_vr_fixo.set('')
        self.valor_vr.set('')
        self.vr_fixo.set(0)
        self.valor_va_fixo.set('')
        self.valor_va.set('')
        self.va_fixo.set(0)
        self.valor_vt_fixo.set('')
        self.vt_fixo.set(0)
        self.vt_percentual.set("6")
        self.atraso_horas.set("")
        self.atraso_minutos.set("")
        self.faltas.set("")
        self.atualizar_pensao()
        self.atualizar_campos()
        self.text.config(state='normal')
        self.text.delete('1.0', 'end')
        self.text.config(state='disabled')

    def salvar_pdf(self, recebimentos, descontos, total_recebimento, total_desconto, liquido):
        """Salva a folha de pagamento em um arquivo PDF."""
        file_path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")],
            title="Salvar Holerite como PDF"
        )
        if not file_path:
            return

        doc = SimpleDocTemplate(file_path, pagesize=letter)
        styles = getSampleStyleSheet()
        story = []

        # Título
        title_style = ParagraphStyle(
            'TitleStyle',
            parent=styles['Heading1'],
            fontSize=16,
            spaceAfter=20,
            alignment=1  # Centered
        )
        story.append(Paragraph("Holerite", title_style))

        # Recebimentos
        story.append(Paragraph("<b>RECEBIMENTOS</b>", styles['Normal']))
        recebimento_data = [['Descrição', 'Valor']]
        for desc, val in recebimentos:
            recebimento_data.append([desc, formatar(val)])
        recebimento_table = Table(recebimento_data, colWidths=[4*inch, 2*inch])
        recebimento_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('GRID', (0,0), (-1,-1), 1, colors.black),
            ('BOX', (0,0), (-1,-1), 1, colors.black),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold')
        ]))
        story.append(recebimento_table)
        story.append(Spacer(1, 0.2*inch))

        # Descontos
        story.append(Paragraph("<b>DESCONTOS</b>", styles['Normal']))
        desconto_data = [['Descrição', 'Valor']]
        for desc, val in descontos:
            desconto_data.append([desc, formatar(val)])
        desconto_table = Table(desconto_data, colWidths=[4*inch, 2*inch])
        desconto_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('GRID', (0,0), (-1,-1), 1, colors.black),
            ('BOX', (0,0), (-1,-1), 1, colors.black),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold')
        ]))
        story.append(desconto_table)
        story.append(Spacer(1, 0.2*inch))

        # Totais
        total_data = [
            ["TOTAL RECEBIMENTOS:", formatar(total_recebimento)],
            ["TOTAL DESCONTOS:", formatar(total_desconto)],
            ["VALOR LÍQUIDO A RECEBER:", formatar(liquido)]
        ]
        total_table = Table(total_data, colWidths=[4*inch, 2*inch])
        total_table.setStyle(TableStyle([
            ('GRID', (0,0), (-1,-1), 1, colors.black),
            ('BOX', (0,0), (-1,-1), 1, colors.black),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold')
        ]))
        story.append(total_table)
        story.append(Spacer(1, 0.2*inch))
        
        # Disclaimer
        disclaimer_style = ParagraphStyle(
            'DisclaimerStyle',
            parent=styles['Normal'],
            fontSize=8,
            spaceAfter=10,
            alignment=4 # Justified
        )
        disclaimer_text = "OBS.: OS VALORES GERADOS PODEM VARIAR PARA MAIS OU PARA MENOS, CASO TENHA ALGUMA DUVIDA ENTRE EM CONTATO COM SEU RH."
        story.append(Paragraph(disclaimer_text, disclaimer_style))
        
        # Assinatura
        story.append(Paragraph("<b>ATENCIOSAMENTE<br/>PROGRAMADORES</b>", styles['Normal']))

        try:
            doc.build(story)
            messagebox.showinfo("Sucesso", f"Holerite salvo com sucesso em:\n{file_path}")
        except Exception as e:
            messagebox.showerror("Erro", f"Não foi possível salvar o arquivo: {e}")


    def mostrar_popup(self, recebimentos, descontos, total_recebimento, total_desconto, liquido):
        """
        Função aprimorada para exibir o holerite de forma clara e responsiva.
        """
        top = tk.Toplevel(self)
        top.title('Holerite')
        top.geometry('600x480')
        top.transient(self)
        top.grab_set()

        # Usar um frame principal para o conteúdo com scrollbar
        container = ttk.Frame(top)
        container.pack(fill='both', expand=True, padx=10, pady=10)

        canvas_popup = tk.Canvas(container, bg='#f0f0f0')
        scrollbar_popup = ttk.Scrollbar(container, orient='vertical', command=canvas_popup.yview)
        scrollable_frame = ttk.Frame(canvas_popup)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas_popup.configure(
                scrollregion=canvas_popup.bbox("all")
            )
        )
        
        canvas_popup.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas_popup.configure(yscrollcommand=scrollbar_popup.set)
        
        canvas_popup.pack(side="left", fill="both", expand=True)
        scrollbar_popup.pack(side="right", fill="y")
        
        # Título
        ttk.Label(scrollable_frame, text="Holerite", font=('Segoe UI', 16, 'bold')).pack(pady=10)

        # Frame para as colunas de recebimentos e descontos
        columns_frame = ttk.Frame(scrollable_frame)
        columns_frame.pack(fill='x', expand=True)
        columns_frame.grid_columnconfigure(0, weight=1)
        columns_frame.grid_columnconfigure(1, weight=1)

        # Coluna de Recebimentos
        recebimentos_frame = ttk.LabelFrame(columns_frame, text="RECEBIMENTOS")
        recebimentos_frame.grid(row=0, column=0, sticky='nsew', padx=5)
        recebimentos_frame.grid_columnconfigure(0, weight=1)

        # Coluna de Descontos
        descontos_frame = ttk.LabelFrame(columns_frame, text="DESCONTOS")
        descontos_frame.grid(row=0, column=1, sticky='nsew', padx=5)
        descontos_frame.grid_columnconfigure(0, weight=1)
        
        # Adicionar os itens de recebimento
        for i, (desc, val) in enumerate(recebimentos):
            row_frame = ttk.Frame(recebimentos_frame)
            row_frame.pack(fill='x', expand=True, padx=5, pady=2)
            ttk.Label(row_frame, text=desc).pack(side='left', anchor='w')
            ttk.Label(row_frame, text=formatar(val), foreground='green').pack(side='right', anchor='e')

        # Adicionar os itens de desconto
        for i, (desc, val) in enumerate(descontos):
            row_frame = ttk.Frame(descontos_frame)
            row_frame.pack(fill='x', expand=True, padx=5, pady=2)
            ttk.Label(row_frame, text=desc).pack(side='left', anchor='w')
            ttk.Label(row_frame, text=formatar(val), foreground='red').pack(side='right', anchor='e')
        
        # Adicionar totais e valor líquido abaixo das colunas
        summary_frame = ttk.Frame(scrollable_frame)
        summary_frame.pack(fill='x', padx=5, pady=10)
        summary_frame.grid_columnconfigure(0, weight=1)
        
        ttk.Separator(summary_frame, orient='horizontal').grid(row=0, column=0, sticky='ew', pady=(10, 5))

        ttk.Label(summary_frame, text=f"TOTAL RECEBIMENTOS: {formatar(total_recebimento)}", font=('Segoe UI', 12, 'bold'), foreground='blue').grid(row=1, column=0, sticky='e', pady=(10, 2))
        ttk.Label(summary_frame, text=f"TOTAL DESCONTOS: {formatar(total_desconto)}", font=('Segoe UI', 12, 'bold'), foreground='red').grid(row=2, column=0, sticky='e', pady=(2, 10))

        ttk.Label(summary_frame, text=f"VALOR LÍQUIDO A RECEBER: {formatar(liquido)}", font=('Segoe UI', 14, 'bold'), foreground='green').grid(row=3, column=0, sticky='ew', pady=10)
        
        # Disclaimer e assinatura
        ttk.Label(summary_frame, text="OBS.: OS VALORES GERADOS PODEM VARIAR PARA MAIS OU PARA MENOS, CASO TENHA ALGUMA DUVIDA ENTRE EM CONTATO COM SEU RH.", font=('Segoe UI', 9), wraplength=550).grid(row=4, column=0, sticky='ew', pady=(20, 5))
        
        ttk.Label(summary_frame, text="ATENCIOSAMENTE\nPROGRAMADORES", font=('Segoe UI', 10, 'bold')).grid(row=5, column=0, sticky='ew', pady=5)

        # Botão para salvar como PDF
        ttk.Button(top, text="Salvar PDF", command=lambda: self.salvar_pdf(recebimentos, descontos, total_recebimento, total_desconto, liquido)).pack(pady=5)
        ttk.Button(top, text="Fechar", command=top.destroy).pack(pady=5)
        top.wait_window()

    def calcular(self):
        try:
            if len(self.ano.get()) != 4 or not self.ano.get().isdigit():
                messagebox.showerror('Erro', 'Digite um ano com 4 dígitos válido')
                return
            mes = int(self.mes.get())
            ano = int(self.ano.get())
            valor = float(self.valor.get().replace(',', '.'))
            dias = monthrange(ano, mes)[1]
            
            # Ajuste de salário base
            if self.tipo_valor.get() == 'diario':
                if self.tipo_calculo.get() == 'mes':
                    salario = valor * dias
                    dias_calc = dias
                else:
                    dia_ini = simpledialog.askinteger('Data Início', f'Dia inicial (1 a {dias}):', minvalue=1, maxvalue=dias, parent=self)
                    if dia_ini is None:
                        return
                    dias_calc = dias - dia_ini + 1
                    salario = valor * dias_calc
            else:
                salario = valor
                dias_calc = dias
            
            # Ajuste de pensão
            pensao = 0
            if self.paga_pensao.get():
                if self.tipo_pensao.get() == 'percent':
                    try:
                        perc = float(self.valor_pensao.get().replace(',', '.'))
                    except:
                        perc = 0
                    pensao = salario * perc / 100
                else:
                    try:
                        pensao = float(self.valor_pensao.get().replace(',', '.'))
                    except:
                        pensao = 0
            
            recebimentos = []
            descontos = []

            if self.tipo_contrato.get() == 'CLT':
                h_extras = float(self.horas.get().replace(',', '.') if self.horas.get() else 0)
                perc_extra = float(self.percentual.get().replace(',', '.') if self.percentual.get() else 0)
                if h_extras > 0 and perc_extra == 0:
                    messagebox.showerror('Erro', 'Informe o percentual das horas extras')
                    return
                v_h = val_hora(valor if self.tipo_valor.get() == 'diario' else salario / dias_calc)
                val_h_extras = calc_h_extra(v_h, h_extras, perc_extra) if h_extras > 0 else 0
                
                # Descontos atraso e faltas
                atraso_h = float(self.atraso_horas.get() if self.atraso_horas.get() else 0)
                atraso_m = float(self.atraso_minutos.get() if self.atraso_minutos.get() else 0)
                valor_atraso = v_h * (atraso_h + atraso_m / 60)
                faltas = float(self.faltas.get() if self.faltas.get() else 0)
                
                if self.tipo_valor.get() == 'diario':
                    valor_falta = valor * faltas
                else:
                    valor_dia_mensal = salario / dias
                    valor_falta = valor_dia_mensal * faltas
                
                salario_bruto = salario + val_h_extras
                inss = calc_inss(salario_bruto)
                base_irrf = salario_bruto - inss
                irrf = calc_irrf(base_irrf)
                
                if self.vt_fixo.get():
                    try:
                        vt = float(self.valor_vt_fixo.get().replace(',', '.'))
                    except:
                        vt = 0
                else:
                    vt_pct = float(self.vt_percentual.get().replace(',', '.') if self.vt_percentual.get() else 6)
                    if vt_pct > 6:
                        vt_pct = 6
                    vt = salario_bruto * vt_pct / 100

                uteis = count_uteis(ano, mes)
                if self.vr_fixo.get():
                    try:
                        desc_vr = float(self.valor_vr_fixo.get().replace(',', '.'))
                    except:
                        desc_vr = 0
                else:
                    vr = float(self.valor_vr.get().replace(',', '.') if self.valor_vr.get() else 0)
                    desc_vr = vr * uteis * 0.2
                
                if self.va_fixo.get():
                    try:
                        desc_va = float(self.valor_va_fixo.get().replace(',', '.'))
                    except:
                        desc_va = 0
                else:
                    va = float(self.valor_va.get().replace(',', '.') if self.valor_va.get() else 0)
                    desc_va = va * uteis * 0.2
                
                recebimentos.append(('Salário Bruto', salario_bruto))
                recebimentos.append(('Salário Base', salario))
                if val_h_extras > 0:
                    recebimentos.append(('Horas Extras', val_h_extras))
                
                descontos.append(('INSS', inss))
                descontos.append(('IRRF', irrf))
                if pensao > 0:
                    descontos.append(('Pensão Alimentícia', pensao))
                descontos.append(('Vale Transporte', vt))
                if desc_vr > 0:
                    descontos.append(('Vale Refeição', desc_vr))
                if desc_va > 0:
                    descontos.append(('Vale Alimentação', desc_va))
                if valor_atraso > 0:
                    descontos.append(('Atraso', valor_atraso))
                if valor_falta > 0:
                    descontos.append(('Faltas', valor_falta))

                total_descontos = inss + irrf + pensao + vt + desc_vr + desc_va + valor_atraso + valor_falta
                total_recebimentos = salario_bruto
                liquido = total_recebimentos - total_descontos

            elif self.tipo_contrato.get() == 'PJ':
                irpj = salario * 0.15
                csll = salario * 0.09
                pis_cofins = salario * 0.065
                iss = salario * 0.035
                total_descontos = irpj + csll + pis_cofins + iss + pensao
                total_recebimentos = salario
                liquido = total_recebimentos - total_descontos
                
                recebimentos.append(('Faturamento', salario))
                descontos.append(('IRPJ (15%)', irpj))
                descontos.append(('CSLL (9%)', csll))
                descontos.append(('PIS/COFINS (6,5%)', pis_cofins))
                descontos.append(('ISS (3,5%)', iss))
                if pensao > 0:
                    descontos.append(('Pensão Alimentícia', pensao))

            elif self.tipo_contrato.get() == 'MEI':
                MEI_INSS = 75.90
                MEI_ICMS = 1.00
                MEI_ISS = 5.00
                tipo_ativ = MEIPopup(self).result
                if tipo_ativ is None:
                    return
                if tipo_ativ == 1:
                    das = MEI_INSS + MEI_ICMS
                elif tipo_ativ == 2:
                    das = MEI_INSS + MEI_ISS
                else:
                    das = MEI_INSS + MEI_ICMS + MEI_ISS
                total_descontos = das + pensao
                total_recebimentos = salario
                liquido = total_recebimentos - total_descontos
                
                recebimentos.append(('Faturamento', salario))
                descontos.append(('DAS (mensal)', das))
                if pensao > 0:
                    descontos.append(('Pensão Alimentícia', pensao))
            
            self.mostrar_popup(recebimentos, descontos, total_recebimentos, total_descontos, liquido)

        except Exception as e:
            messagebox.showerror('Erro', f'Erro: {e}')

if __name__ == '__main__':
    app = Calculadora()
    app.mainloop()

