# Importamos las librerias requeridas para la implementación del ejercicio

import sqlite3
import pandas as pd
import openpyxl
import smtplib
from email.message import EmailMessage
from dotenv import load_dotenv
import os

path_base = os.getcwd()

# Insumos
path_resultados = os.path.join(path_base, 'Resultados')
path_env = os.path.join(path_base)

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

    def cobro_peticiones(self, empresa, peticiones_exitosas, peticiones_fallidas, peticiones_totales, precios, limites,descuentos, porcentajes, iva):
        total = 0
        if empresa == 'Innovexa Solutions':
            total = peticiones_exitosas*precios['Innovexa Solutions'] + peticiones_exitosas*precios['Innovexa Solutions']*iva
        elif empresa == 'NexaTech Industries':
            if peticiones_totales <= limites['NexaTech Industries'][0]:
                total = peticiones_exitosas*precios['NexaTech Industries'][0] + peticiones_exitosas*precios['NexaTech Industries'][0]*iva
            elif peticiones_totales <= limites['NexaTech Industries'][1]:
                total = peticiones_exitosas*precios['NexaTech Industries'][1] + peticiones_exitosas*precios['NexaTech Industries'][1]*iva
            else:
                total = peticiones_exitosas*precios['NexaTech Industries'][2] + peticiones_exitosas*precios['NexaTech Industries'][2]*iva
        elif empresa == 'QuantumLeap Inc.':
            total = peticiones_exitosas*precios['QuantumLeap Inc.'] + peticiones_exitosas*precios['QuantumLeap Inc.']*iva
        elif empresa == 'Zenith Corp.':
            if peticiones_totales >= 0 and peticiones_totales <= limites['Zenith Corp.']:
                total = peticiones_exitosas*precios['Zenith Corp.'][0] + peticiones_exitosas*precios['Zenith Corp.'][0]*iva
            elif peticiones_totales > limites['Zenith Corp.']:
                total = peticiones_exitosas*precios['Zenith Corp.'][1] + peticiones_exitosas*precios['Zenith Corp.'][1]*iva
            if peticiones_fallidas >= descuentos['Zenith Corp.']:
                total = total - total*porcentajes['Zenith Corp.']
        elif empresa == 'FusionWave Enterprises':
            total = peticiones_exitosas*precios['FusionWave Enterprises'] + peticiones_exitosas*precios['FusionWave Enterprises']*iva
            if descuentos['FusionWave Enterprises'][0] <= peticiones_fallidas <= descuentos['FusionWave Enterprises'][1]:
                total = total - total*porcentajes['FusionWave Enterprises'][0]  
            elif peticiones_fallidas > descuentos['FusionWave Enterprises'][1]:
                total = total - total*porcentajes['FusionWave Enterprises'][1]
        return total

    def calcular_comision(self, mes, precios, iva):
        self.obtener_datos(mes)
        
        resultado = pd.read_sql("SELECT * FROM resultado", self.conn)
        commerce = pd.read_sql("SELECT * FROM commerce", self.conn)
        
        resultado_tab = pd.crosstab(resultado['commerce_id'], resultado['ask_status'])
        resultado_tab['Total'] = resultado_tab['Successful'] + resultado_tab['Unsuccessful']

        resultado_tab = resultado_tab.merge(commerce[['commerce_id', 'commerce_name', 'commerce_nit', 'commerce_email', 'commerce_status']], 
                                            left_on='commerce_id', right_on='commerce_id', how='left')
    
        resultado_tab['Cobro Total'] = resultado_tab.apply(
            lambda row: self.cobro_peticiones(row['commerce_name'], row['Successful'], row['Unsuccessful'], row['Total'], precios, limites, descuentos, porcentajes, iva) 
            if row['commerce_status'] == 'Active' else 0, axis=1)
    
    
        resultado_tab['Valor_comision'] = resultado_tab.apply(lambda row: row['Cobro Total'] / (1 + iva) if row['commerce_status'] == 'Active' else 0, axis=1)
        resultado_tab['Valor_iva'] = resultado_tab.apply(lambda row: row['Valor_comision'] * iva if row['commerce_status'] == 'Active' else 0, axis=1)
        resultado_tab['Valor_Total'] = resultado_tab['Cobro Total']
    
        resultado_tab['Fecha-Mes'] = mes
    
        return resultado_tab

    
    def enviar_correo(self, archivo_excel, destinatario, remitente, contrasena):
        
        msg = EmailMessage()
        msg.set_content(f"Hola, espero se encuentren muy bien,\n\nAdjunto el archivo donde se encuentra los resultados de las comisiones calculadas para cada empresa.\n\nSaludos")
        msg['Subject'] = 'Resultados de Comisiones'
        msg['From'] = remitente
        msg['To'] = destinatario
    
        with open(archivo_excel, 'rb') as f:
            file_data = f.read()
            file_name = f.name
    
        msg.add_attachment(file_data, maintype='application', subtype='octet-stream', filename=file_name)
    
        # Conectar al servidor SMTP de Outlook y enviar el mensaje
        smtp_server = 'smtp.office365.com'
        smtp_port = 587
    
        try:
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()  
                server.login(remitente, contrasena)
                server.send_message(msg)
                print(f"Correo electr�nico enviado exitosamente a {destinatario}.")
        except Exception as e:
            print(f"Error al enviar el correo a {destinatario}: {e}")
            
            
            
# Conectar a la base de datos SQLite

conn = sqlite3.connect('C:/Prueba_ecosistemas/database.sqlite')
calculo = Calculo_comisiones(conn)

# Generamos los diccionarios necesarios dentro de la automatización
precios = {
    'Innovexa Solutions': 300,
    'NexaTech Industries': [250,  # Asignar si hay entre 0 a 10.000 peticiones totales
                            200,  # Asignar si hay entre 10.001 a 20.000 peticiones totales
                            170], # Asignar si hay más de 20.001 peticiones totales
    'QuantumLeap Inc.': 600, 
    'Zenith Corp.': [250,  # Asignar si hay entre 0 a 22.000 peticiones totales
                     130], # Asignar si hay más de 22.001 peticiones totales
    'FusionWave Enterprises': 300
}
limites = {
    'NexaTech Industries': [10000, 20000],  # Límites de peticiones totales
    'Zenith Corp.': 22000  # Límites de peticiones totales
}
descuentos = {
    'FusionWave Enterprises': [2500, 4500],  # Rango para descuento
    'Zenith Corp.': 6000  # Valor para descuento
}
porcentajes = {
    'FusionWave Enterprises': [0.05, 0.08],  # Rango para descuento
    'Zenith Corp.': 0.05  # Valor para descuento
}


iva = 0.19 # Se añade el valor del IVA colombiano
mes = '2024-07' # Se añde el mes que se quiere desglosar, como ejemplo tomamos Julio del 2024


# Calcular comisiones según la información suministrada anteriormente

resultado_tab = calculo.calcular_comision(mes, precios, iva)

archivo_excel = 'resultados_comisiones.xlsx'
df_final = resultado_tab[['Fecha-Mes', 'commerce_name', 'commerce_nit', 'Valor_comision', 'Valor_iva', 'Valor_Total', 'commerce_email']]
df_final = df_final.rename(columns={'commerce_name': 'Nombre', 'commerce_nit': 'Nit', 'commerce_email': 'Correo'})
df_final.to_excel(archivo_excel, index=False)

load_dotenv(path_env)
correo_remitente = os.getenv('CORREO_REMITENTE')
correo_ejecutor = os.getenv('CORREO_EJECUTOR')
password = os.getenv('PASSWORD')

date_str = str(mes)
date_str

# Agrega la fecha al nombre de los archivos de salida
xlsx_filename = os.path.join(path_resultados, f'Cobro_comisi�n_{date_str}.xlsx')
df_final.to_excel(xlsx_filename, index=False, header=False)
# Enviar el correo como ejecutor
archivo_excel = xlsx_filename
calculo.enviar_correo(archivo_excel, correo_ejecutor, correo_remitente, password)

