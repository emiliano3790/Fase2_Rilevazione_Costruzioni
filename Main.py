# coding=utf-8
from __future__ import division
import os
import Tools as tl
from xlsxwriter.utility import xl_rowcol_to_cell
import glob

input_dir = # Cartella con i poligoni di input
stack_dir = 'Stack' # Cartella con gli stack dal 1999 al 2018
output_dir = 'Output'
stack_cropped_dir = 'Stack_Cropped'
statistics_dir = 'Statistics'

index_name_list = ['Coefficient', 'SAVI', 'NDVI', 'NDBI1', 'NDBI2', 'MNDWI']
# year_list = ['2003', '2004', '2005', '2006', '2007', '2008', '2009', '2010', '2011', '2013', '2014', '2015', '2016', '2017', '2018'] # Caso LS8
year_list = ['2003', '2004', '2005', '2006', '2007', '2008', '2009', '2010', '2011', '2012', '2013', '2014', '2015', '2016', '2017', '2018'] # Caso LS7
legend_name_list = ['Poligono', 'Intorno', 'Delta assoluto']
let_list_excel_diff = ['R', 'S', 'T', 'U', 'V', 'W']
let_list_excel_pol = ['B', 'C', 'D', 'E', 'F', 'G']
let_list_excel_int = ['J', 'K', 'L', 'M', 'N', 'O']

# Serve semplicemente per il nome dei file
# execution_type = 'stack_LS5-LS8_'
execution_type = 'stack_LS5-LS7_'

stack_dir_path = os.getcwd() + '/' + stack_dir # Cartella degli stack che vado a tagliare sul poligono di interesse

# Controllo l'esistenza della cartella di output_dir
if not os.path.exists(os.getcwd() + '/' + output_dir):
	os.mkdir(os.getcwd() + '/' + output_dir)

# Seleziono i vari geojson che simulano l'area incendiata
for geojson in os.listdir(os.getcwd() + '/' + input_dir):
	geojson_name = geojson[:geojson.index(".")]  # Prendo il solo nome del file senza estensione: 2_Ex_2005-2011
	print 'GeoJSON:', geojson_name
	dest_stack_cropped_dir = os.getcwd() + '/' + output_dir + '/' + geojson_name + '/' + stack_cropped_dir # stack cropped sul geojson
	excel_statistics_dir = os.getcwd() + '/' + output_dir + '/' + geojson_name + '/' + statistics_dir # Qua salvo le statistiche
	if not os.path.exists(dest_stack_cropped_dir):
		os.makedirs(dest_stack_cropped_dir)
	if not os.path.exists(excel_statistics_dir):
		os.makedirs(excel_statistics_dir)
	sheet_list, workbook_list = tl.open_stat_files(geojson_name)  # Apre i file excel delle statistiche: nome-geojson_nome-stat.xlsx
	geojson_path = os.getcwd() + '/' + input_dir + '/' + geojson
	year_min_lim = geojson[-17:-13]
	year_sup_lim = geojson[-12:-8]
	print 'year_min_lim, year_sup_lim', year_min_lim, year_sup_lim
	for sheet in sheet_list:
		sheet.write(0, 0, geojson_name)
		stat_type_row = 1
		stat_type_col = 0
		tl.init_excel_file(sheet, stat_type_row, stat_type_col, 'Polygon', year_list, index_name_list)
		stat_type_col += len(year_list) + 2
		tl.init_excel_file(sheet, stat_type_row, stat_type_col, 'Contorno', year_list, index_name_list)
		stat_type_col += len(year_list) + 2
		tl.init_excel_file(sheet, stat_type_row, stat_type_col, 'Differenza', year_list, index_name_list)
	tl.core_function(geojson_path, stack_dir_path, dest_stack_cropped_dir, sheet_list)
	tl.calc_difference(sheet_list)
	tl.close_stat_file(workbook_list)
	# Per spostare i file delle statistiche li rinomino
	for xlsx_file in glob.glob("*.xlsx"): # Fa la ricerca nella cwd
		os.rename(os.getcwd() + '/' + xlsx_file, excel_statistics_dir + '/' + xlsx_file)

	# Ora devo creare i grafici
	for i in range(0, len(sheet_list)):
		z = 0
		row_chart = 21
		for index in index_name_list:
			chart_diff = workbook_list[i].add_chart({'type': 'line'})
			chart_pol = workbook_list[i].add_chart({'type': 'line'})
			chart_int = workbook_list[i].add_chart({'type': 'line'})
			chart_diff.set_x_axis({'name': 'Year'})
			chart_diff.set_title({'name': index})  # Intestazione grafico
			chart_pol.set_x_axis({'name': 'Year'})
			chart_pol.set_title({'name': index})  # Intestazione grafico
			chart_int.set_x_axis({'name': 'Year'})
			chart_int.set_title({'name': index})  # Intestazione grafico
			string_chart_diff = '=Sheet1!$' + let_list_excel_diff[z] + '$5:$' + let_list_excel_diff[z] + '$19'
			string_chart_pol = '=Sheet1!$' + let_list_excel_pol[z] + '$5:$' + let_list_excel_pol[z] + '$19'
			string_chart_int = '=Sheet1!$' + let_list_excel_int[z] + '$5:$' + let_list_excel_int[z] + '$19'
			# print string_values
			chart_diff.add_series({
				'categories': '=Sheet1!$Q$5:$Q$19',
				'values': string_chart_diff,
			})
			chart_pol.add_series({
				'categories': '=Sheet1!$Q$5:$Q$19',
				'values': string_chart_pol,
			})
			chart_int.add_series({
				'categories': '=Sheet1!$Q$5:$Q$19',
				'values': string_chart_int,
			})
			casel_diff_chart = 'Q' + str(row_chart)
			sheet_list[i].insert_chart(casel_diff_chart, chart_diff)
			casel_pol_chart = 'A' + str(row_chart)
			sheet_list[i].insert_chart(casel_pol_chart, chart_pol)
			casel_int_chart = 'I' + str(row_chart)
			sheet_list[i].insert_chart(casel_int_chart, chart_int)
			row_chart = row_chart + 16
			z = z + 1






	# 	for legend_name in legend_name_list:
	# 		sheet.write(0, column_legend, geojson_name)
	# 		sheet.write(1, column_legend, legend_name)
	# 		row_year = 4
	# 		for year in year_list:
	# 			sheet.write(row_year, column_legend, year)
	# 			row_year = row_year + 1
	# 		for index_name in index_name_list:
	# 			sheet.write(3, column_index, index_name)
	# 			column_index = column_index + 1
	# 		column_legend = column_legend + 8
	# 		column_index = column_index + 2
	# first_value_row_index = 2
	# first_value_column_index = 1
	# tl.core_function(geojson_path, stack_dir_path, dest_stack_cropped_dir, first_value_row_index, first_value_column_index, sheet_list)
	# for sheet in sheet_list:
	# 	for row in range(4, 19):
	# 		for col in range(1, 7):
	# 			polygon_item = xl_rowcol_to_cell(row, col)
	# 			intorno_item = xl_rowcol_to_cell(row, col + 8)
	# 			dest_cell = xl_rowcol_to_cell(row, col + 16)
	# 			formula = '=ABS(-' + polygon_item + '+' + intorno_item + ')' # Formula: intorno - poligono
	# 			esito = sheet.write_formula(dest_cell, formula)

