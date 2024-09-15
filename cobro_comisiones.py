import sqlite3
import pandas as pd
import smtplib
from email.message import EmailMessage
import openpyxl

class Calculo_comisiones:
    
    def __init__(self, conn):
        self.conn = conn
        self.cursor = self.conn.cursor()

    def obtener_datos(self, mes):
        query = f"""
        CREATE TABLE IF NOT EXISTS resultado AS
        SELECT A.*, C.* 
        FROM apicall AS A
        LEFT JOIN commerce AS C
        ON A.commerce_id = C.commerce_id
        WHERE strftime('%Y-%m', A.date_api_call) = '{mes}'
        """
        self.cursor.execute(query)
        self.conn.commit()

    def cobro_peticiones(self, empresa, peticiones_exitosas, peticiones_fallidas, peticiones_totales, precios, iva):
        total = 0
        if empresa == 'Innovexa Solutions':
            total = peticiones_exitosas * precios['Innovexa Solutions'] + peticiones_exitosas * precios['Innovexa Solutions'] * iva
        elif empresa == 'NexaTech Industries':
            if peticiones_totales <= 10000:
                total = peticiones_exitosas * precios['NexaTech Industries'][0] + peticiones_exitosas * precios['NexaTech Industries'][0] * iva
            elif peticiones_totales <= 20000:
                total = peticiones_exitosas * precios['NexaTech Industries'][1] + peticiones_exitosas * precios['NexaTech Industries'][1] * iva
            else:
                total = peticiones_exitosas * precios['NexaTech Industries'][2] + peticiones_exitosas * precios['NexaTech Industries'][2] * iva
        elif empresa == 'QuantumLeap Inc.':
            total = peticiones_exitosas * precios['QuantumLeap Inc.'] + peticiones_exitosas * precios['QuantumLeap Inc.'] * iva
        elif empresa == 'Zenith Corp.':
            if peticiones_totales >= 0 and peticiones_totales <= 22000:
                total = peticiones_exitosas * precios['Zenith Corp.'][0] + peticiones_exitosas * precios['Zenith Corp.'][0] * iva
            elif peticiones_totales >= 22001:
                total = peticiones_exitosas * precios['Zenith Corp.'][1] + peticiones_exitosas * precios['Zenith Corp.'][1] * iva
            if peticiones_fallidas >= 6000:
                total = total - total * 0.05
        elif empresa == 'FusionWave Enterprises':
            total = peticiones_exitosas * precios['FusionWave Enterprises'] + peticiones_exitosas * precios['FusionWave Enterprises'] * iva
            if 2500 <= peticiones_fallidas <= 4500:
                total = total - total * 0.05  # Descuento del 5% antes de IVA
            elif peticiones_fallidas > 4501:
                total = total - total * 0.08
        return total

    def calcular_comision(self, mes, precios, iva):
        self.obtener_datos(mes)
        
        resultado = pd.read_sql("SELECT * FROM resultado", self.conn)
        commerce = pd.read_sql("SELECT * FROM commerce", self.conn)
        
        resultado_tab = pd.crosstab(resultado['commerce_id'], resultado['ask_status'])
        resultado_tab['Total'] = resultado_tab['Successful'] + resultado_tab['Unsuccessful']

        resultado_tab = resultado_tab.merge(commerce[['commerce_id', 'commerce_name', 'commerce_nit', 'commerce_email']], 
                                            left_on='commerce_id', right_on='commerce_id', how='left')
        
        resultado_tab['Cobro Total'] = resultado_tab.apply(
            lambda row: self.cobro_peticiones(row['commerce_name'], row['Successful'], row['Unsuccessful'], row['Total'], precios, iva), axis=1)

        resultado_tab['Fecha-Mes'] = mes
        resultado_tab['Valor_comision'] = resultado_tab['Cobro Total'] / (1 + iva)
        resultado_tab['Valor_iva'] = resultado_tab['Valor_comision'] * iva
        resultado_tab['Valor_Total'] = resultado_tab['Cobro Total']
        
        return resultado_tab
    
    def enviar_correo(self, archivo_excel, destinatario, remitente, contrasena):
        # Crear el mensaje
        msg = EmailMessage()
        msg.set_content("Hola,\n\nAdjunto se encuentra el archivo con los resultados de las comisiones calculadas.\n\nSaludos,\nTu equipo")
        msg['Subject'] = 'Resultados de Comisiones'
        msg['From'] = remitente
        msg['To'] = destinatario

        # Adjuntar el archivo Excel
        with open(archivo_excel, 'rb') as f:
            file_data = f.read()
            file_name = f.name

        msg.add_attachment(file_data, maintype='application', subtype='octet-stream', filename=file_name)

        # Conectar al servidor SMTP de Outlook y enviar el mensaje
        smtp_server = 'smtp.office365.com'
        smtp_port = 587

        try:
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()  # Establecer una conexión segura
                server.login(remitente, contrasena)
                server.send_message(msg)
                print("Correo electrónico enviado exitosamente.")
        except Exception as e:
            print(f"Error al enviar el correo: {e}")


# Conectar a la base de datos SQLite
conn = sqlite3.connect('C:/Prueba_ecosistemas/database.sqlite')

# Crear instancia de la clase
calculo = Calculo_comisiones(conn)

# Definir precios y el IVA
precios = {
    'Innovexa Solutions': 300,
    'NexaTech Industries': [250,
                            200, 
                            170],
    'QuantumLeap Inc.': 600,
    'Zenith Corp.': [250,
                     130],
    'FusionWave Enterprises': 300
}
iva = 0.19

# Calcular comisiones para un mes dado
mes = '2024-07'
resultado_tab = calculo.calcular_comision(mes, precios, iva)

# Guardar el DataFrame como archivo Excel Y definir las columnas necesarias según
#lo estipulado en el correo

archivo_excel = 'resultados_comisiones.xlsx'
df_final = resultado_tab[['Fecha-Mes', 'commerce_name', 'commerce_nit', 'Valor_comision', 'Valor_iva', 'Valor_Total', 'commerce_email']]
df_final = df_final.rename(columns={'commerce_name': 'Nombre', 'commerce_nit': 'Nit', 'commerce_email': 'Correo'})
df_final.to_excel(archivo_excel, index=False)

# Enviar el correo
calculo.enviar_correo(archivo_excel, 'danielvallejo20@outlook.com', 'danielvallejo20@outlook.com', 'xafuna20')


df_final.to_excel('C:\Prueba_ecosistemas.xlsx')
