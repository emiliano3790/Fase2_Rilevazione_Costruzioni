# coding=utf-8
from __future__ import division
import rasterio
import os
import numpy as np
import json
import collections
import xlsxwriter
from rasterio.mask import mask
from scipy import stats
from random import randint

cloud_dir = 'cloud_mosaic'

min_dist = 20 # distanza minima dal poligono per cui cerco i pixel di contorno. Provare con 20/15
max_dist = 50 # distanza massima dal poligono per cui cerco i pixel di contorno. Provare con 60/70

LS7_list = ['2012', '2013', '2014', '2015', '2016', '2017', '2018']
stat_name_list = ['mean', 'min', 'max', 'devstd', 'var', 'perc25', 'perc50', 'perc75', 'perc98']


def open_stat_files(geojson_name):
    sheet_list = []
    workbook_list = []
    for stat_name in stat_name_list:
        file_name = geojson_name + '_' + stat_name + ".xlsx"
        workbook = xlsxwriter.Workbook(file_name)
        sheet = workbook.add_worksheet()
        sheet_list.append(sheet)
        workbook_list.append(workbook)
    return sheet_list, workbook_list

# Inizializza la struttura dei file excel. 3 blocchi uguali: polygon, contorno e differenza
def init_excel_file(sheet, stat_type_row, stat_type_col, stat_type, year_list, index_list):
    sheet.write(1, stat_type_col, stat_type)
    col_year = stat_type_col + 1
    for year in year_list:
        sheet.write(stat_type_row, col_year, year)
        col_year += 1
    row_index = 2
    col_index = stat_type_col
    for index in index_list:
        sheet.write(row_index, col_index, index)
        row_index += 1


def close_stat_file(workbook_list):
    for workbook in workbook_list:
        workbook.close()


def get_polygon(geojson_path):
    geojson = open(geojson_path, 'r').read()
    readable_json = json.loads(geojson)
    polygon = []
    temp = readable_json['features'][0]['geometry']
    polygon.append(readable_json['features'][0]['geometry'])
    return polygon
    # Il file GeoJSON va chiuso?


def mask_dataset(stack_path, polygon, dest_stack_cropped_dir):
    stack_dataset = rasterio.open(stack_path, 'r')
    stack_name = os.path.basename(stack_path)
    stack_name = stack_name[:stack_name.index(".")]
    stack_cropped, out_transform = mask(stack_dataset, polygon, crop = True, all_touched = True)
    altezza_cropped_array = stack_cropped.shape[1]
    larghezza_cropped_array = stack_cropped.shape[2]
    desc = stack_dataset.descriptions
    stack_cropped_dataset_meta = stack_dataset.meta.copy()
    stack_dataset.close()
    stack_cropped_dataset_meta.update({"driver": "GTiff",
                     "height": stack_cropped.shape[1],
                     "width": stack_cropped.shape[2],
                     "transform": out_transform})
    stack_cropped_tif_path = dest_stack_cropped_dir + '/' + stack_name + '_cropped' + '.tif'
    stack_cropped_tif = rasterio.open(stack_cropped_tif_path, "w", **stack_cropped_dataset_meta)
    stack_cropped_tif.write(stack_cropped)
    stack_cropped_tif.descriptions = desc # Rivedere la cosa della descrizione
    return stack_cropped_tif_path, altezza_cropped_array, larghezza_cropped_array


# Funzione che permette di estrarre una singola banda da un certo stack multispettrale
def get_band_array(stack_path, num_band, SWIR2_band):
    stack_dataset = rasterio.open(stack_path, 'r')
    for i in range(0, num_band):
        # print i, potrei valutare di usare break o continue
        if 'band2' in stack_dataset.descriptions[i]:
            green_array = stack_dataset.read(i + 1, masked = True)
            # print 'Green ok'
        if 'band3' in stack_dataset.descriptions[i]:
            red_array = stack_dataset.read(i + 1, masked = True)
            # print 'Red ok'
        if 'band4' in stack_dataset.descriptions[i]:
            NIR_array = stack_dataset.read(i + 1, masked = True)
            # print 'NIR ok'
        if 'band5' in stack_dataset.descriptions[i]:
            SWIR1_array = stack_dataset.read(i + 1, masked = True)
            # print 'SWIR1 ok'
        if SWIR2_band in stack_dataset.descriptions[i]:
            SWIR2_array = stack_dataset.read(i + 1, masked = True)
            # print 'SWIR2 ok'
    stack_dataset.close()
    return green_array, red_array, NIR_array, SWIR1_array, SWIR2_array


def calculate_stats(green_array, red_array, NIR_array, SWIR1_array, SWIR2_array, column, sheet_list):
    index_array_list = [] # Qua salvo i vari indici calcolati sulla sola area di interesse
    SWIR_average_array = (SWIR1_array + SWIR2_array)/2
    coefficient_array = SWIR_average_array/NIR_array
    index_array_list.append(coefficient_array)
    SAVI_array = ((NIR_array - red_array)*(1 + 0.5))/(NIR_array + red_array + 0.5)
    index_array_list.append(SAVI_array)
    NDVI_array = (NIR_array - red_array)/(NIR_array + red_array)
    index_array_list.append(NDVI_array)
    NDBI1_array = (SWIR1_array - NIR_array)/(SWIR1_array + NIR_array)
    index_array_list.append(NDBI1_array)
    NDBI2_array = (SWIR2_array - NIR_array)/(SWIR2_array + NIR_array) # SWIR2 viene aggiornato automaticamente
    index_array_list.append(NDBI2_array)
    MNDWI_array = (green_array - SWIR1_array)/(green_array + SWIR1_array)
    index_array_list.append(MNDWI_array)
    row = 2
    for index_array in index_array_list:
        sheet_list[0].write(row, column, np.mean(index_array))
        sheet_list[1].write(row, column, np.min(index_array))
        sheet_list[2].write(row, column, np.max(index_array))
        sheet_list[3].write(row, column, np.std(index_array))
        sheet_list[4].write(row, column, np.var(index_array))
        sheet_list[5].write(row, column, np.percentile(index_array, 25))
        sheet_list[6].write(row, column, np.percentile(index_array, 50))
        sheet_list[7].write(row, column, np.percentile(index_array, 75))
        sheet_list[8].write(row, column, np.percentile(index_array, 98))
        row += 1


def cloud_check(rand_row_index, rand_col_index):
	LS5_LS7_cloud_value_list = [2, 4, 8, 16]
    LS8_cloud_value_list = [352, 368, 416, 432, 480, 864, 880, 928, 944, 992, # Cloud
                            328, 392, 840, 904, 1350, # Cloud shadow
                            336, 368, 400, 432, 848, 880, 912, 944, 1352, # Snow/Ice
                            480, 992, # High confidence cloud
                            322, 324, 328, 336, 352, 368, 386, 388, 392, 400, 416, 432, 480, # Low confidence cirrus
                            834, 836, 840, 848, 864, 880, 898, 900, 904, 912, 928, 944, 992] # High confidence cirrus
    cloud_pixel = False # È la variabile che viene restituita dalla funzione e che mi permette di capire se il pixel è coperto da nuvole o meno
    temp_cond = True
    for cloud_tif in os.listdir(os.getcwd() + '/' + cloud_dir):
        cloud_dataset = rasterio.open(os.getcwd() + '/' + cloud_dir + '/' + cloud_tif, 'r')
        cloud_array = cloud_dataset.read(1, masked = True)
        if 'LS5' or 'LS7' in cloud_tif: # Mi serve una regola per capire con che tipo di cloud mosaic sto lavorando
            for cloud_value in LS5_LS7_cloud_value_list:
                if cloud_array[rand_row_index][rand_col_index] == cloud_value: # Il pixel è nuvoloso
                    temp_cond = False
                    break
        elif 'LS8' in cloud_tif:
            for cloud_value in LS8_cloud_value_list:
                if cloud_array[rand_row_index][rand_col_index] == cloud_value: # Il pixel è nuvoloso
                    temp_cond = False
                    break
        if not temp_cond: # Se temp_cond è False allora il pixel è nuvoloso
            cloud_pixel = True # Il pixel è nuvoloso
            break
    return cloud_pixel


def mndwi_check(stack_dir_path, MNDWI_mean_value_list, num_band, rand_row_index, rand_col_index):
    cond_mndwi = True
    for stack in os.listdir(stack_dir_path): # Controllo solo sullo stack dell'anno dell'incendio
        stack_dataset = rasterio.open(stack_dir_path + '/' + stack, 'r')
        for i in range(0, num_band):
            if 'band2' in stack_dataset.descriptions[i]:
                green_array = stack_dataset.read(i + 1, masked=True)
            if 'band5' in stack_dataset.descriptions[i]:
                SWIR1_array = stack_dataset.read(i + 1, masked=True)
        MNDWI_array = (green_array - SWIR1_array)/(green_array + SWIR1_array)
        for MNDWI_mean in MNDWI_mean_value_list:
            if abs(MNDWI_array[rand_row_index][rand_col_index] - MNDWI_mean) <= 0.10: # Provare anche con la seguente soglia: 0.05/0.07/0.09
                cond_mndwi = False
                return cond_mndwi, green_array
    return cond_mndwi, green_array


# Bisogna capire se l'anno dello stack da cui estraggo i pixel è importante o meno
def get_random_pixel(stack_dir_path, stack, lon_alto_sx, lat_alto_sx, lon_basso_dx, lat_basso_dx, altezza_cropped_array, larghezza_cropped_array, geojson_path, MNDWI_mean_value_list, num_band):
    # Prendo gli indici che fanno riferimento al pixel in alto a sinistra e in basso a destra
    stack_path = stack_dir_path + '/' + stack
    stack_dataset = rasterio.open(stack_path, 'r') # Occhio a stack
    row_00, col_00 = stack_dataset.index(lon_alto_sx,lat_alto_sx) # Punto in alto a sinistra
    row_mn, col_mn = stack_dataset.index(lon_basso_dx,lat_basso_dx) # Punto di basso a destra
    stack_dataset.close()
    # A quanto pare devo castare gli indici
    row_00 = int(row_00)
    col_00 = int(col_00)
    row_mn = int(row_mn)
    col_mn = int(col_mn)
    print 'Indici pixel in alto a sinistra:', row_00, col_00
    print 'Indici pixel in basso a destra:', row_mn, col_mn
    # Il numero di pixel da estrarre casualmente == al numero di pixel (nodata???) che formano il poligono.
    # if altezza_cropped_array * larghezza_cropped_array < 30:
    #     num_extracted_pixel_threshold = altezza_cropped_array * larghezza_cropped_array
    # else:
    #     num_extracted_pixel_threshold = 30
    num_extracted_pixel_threshold = 2 # Per i test
    print 'Indici pixel in alto a sinistra della cornice proibita:', row_00 - min_dist, col_00 - min_dist
    print 'Indici pixel in alto a sinistra della cornice proibita:', row_mn + min_dist, col_mn + min_dist
    random_pixel_list = []
    num_extracted_pixel = 0 # Numero di pixel estratti
    while num_extracted_pixel < num_extracted_pixel_threshold:
        rand_row_index = randint(row_00 - max_dist, row_mn + max_dist)
        if rand_row_index < (row_00 - min_dist) or rand_row_index > (row_mn + min_dist):
            rand_col_index = randint(col_00 - max_dist, col_mn + max_dist)
        elif (row_00 - min_dist) <= rand_row_index <= (row_mn + min_dist):
            num_fascia = randint(1,2) # 1 <= num_fascia <= 2
            if num_fascia == 1:
                rand_col_index = randint(col_00 - max_dist, col_00 - min_dist)
            else:
                rand_col_index = randint(col_mn + min_dist, col_mn + max_dist)
        random_pixel = {'riga' : rand_row_index,
                          'colonna' : rand_col_index}
        # Controllo se i 2 indici sono stati estratti, quindi se sto considerando un pixel già preso
        if random_pixel in random_pixel_list:
            print 'Pixel estratto in precedenza', rand_row_index, rand_col_index
            continue # Passo all'iterazione successiva
        else: # Il pixel non è già stato estratto
            # Effettuo ora il controllo sulle nuvole
            if cloud_check(rand_row_index, rand_col_index): # Se la funzione restituisce True allora il pixel è nuvoloso
                continue
            else:
                # Effettuo il controllo sull'MNDWI
                # cond_mndwi, green_array = mndwi_control(stack_dir_path, MNDWI_mean_value_list, num_band, rand_row_index, rand_col_index)
                # if cond_mndwi is False: # Controllo condizione MNDWI
                #     print 'Condizione su MNDWI non rispettata'
                #     continue
                # elif len(MNDWI_mean_value_list) > 15: # In questo caso sto usando dati LS7 (2004-2011 ci posso avere no data)
                #     if green_array[rand_row_index][rand_col_index] == -9999: # -9999 valore nodata per LS7
                #         print 'Il pixel corrisponde a no data'
                #         continue
                # Superata anche la condzione sull'MNDWI il pixel estratto può essere accettato
                print 'Pixel estratto:', rand_row_index, rand_col_index
                num_extracted_pixel += 1
                random_pixel_list.append({'riga' : rand_row_index,
                                          'colonna' : rand_col_index
                                        })
    return random_pixel_list


def get_bound_array(stack_path, random_pixel_list, SWIR2_band, num_band):
    green_array, red_array, NIR_array, SWIR1_array, SWIR2_array = get_band_array(stack_path, num_band, SWIR2_band)
    green_array_bound = np.empty(len(random_pixel_list), dtype = green_array.dtype)
    red_array_bound = np.empty(len(random_pixel_list), dtype = red_array.dtype)
    NIR_array_bound = np.empty(len(random_pixel_list), dtype = NIR_array.dtype)
    SWIR1_array_bound = np.empty(len(random_pixel_list), dtype = SWIR1_array.dtype)
    SWIR2_array_bound = np.empty(len(random_pixel_list), dtype = SWIR2_array.dtype)
    for i in range(0, len(random_pixel_list)):
        pixel = random_pixel_list[i] # pixel = dict
        pixel_row = pixel['riga']
        pixel_col = pixel['colonna']
        print pixel_row, pixel_col
        print 'green_array[pixel_row][pixel_col]', green_array[pixel_row][pixel_col]
        green_array_bound[i] = green_array[pixel_row][pixel_col]
        print 'red_array[pixel_row][pixel_col]', red_array[pixel_row][pixel_col]
        red_array_bound[i] = red_array[pixel_row][pixel_col]
        print 'NIR_array[pixel_row][pixel_col]', NIR_array[pixel_row][pixel_col]
        NIR_array_bound[i] = NIR_array[pixel_row][pixel_col]
        print 'SWIR1_array[pixel_row][pixel_col]', SWIR1_array[pixel_row][pixel_col]
        SWIR1_array_bound[i] = SWIR1_array[pixel_row][pixel_col]
        print 'SWIR2_array[pixel_row][pixel_col]', SWIR2_array[pixel_row][pixel_col]
        SWIR2_array_bound[i] = SWIR2_array[pixel_row][pixel_col]
    return green_array_bound, red_array_bound, NIR_array_bound, SWIR1_array_bound, SWIR2_array_bound


def calc_difference(sheet_list):
    for sheet in sheet_list:
		for row in range(2, 8):
			for col in range(1, 17):
				polygon_item = xl_rowcol_to_cell(row, col)
				intorno_item = xl_rowcol_to_cell(row, col + 17)
				dest_cell = xl_rowcol_to_cell(row, col + 17)
				formula = '=ABS(-' + polygon_item + '+' + intorno_item + ')' # Formula: intorno - poligono
				esito = sheet.write_formula(dest_cell, formula)


def core_function(geojson_path, stack_dir_path, dest_stack_cropped_dir, first_value_row_index, first_value_column_index, sheet_list, n):
    polygon = get_polygon(geojson_path) # Estrae il poligono dal file geojson
    MNDWI_mean_value_list = []

    # Con questo primo ciclo calcolo le statistiche relative all'AOI definita dal poligono
    for stack in os.listdir(stack_dir_path):
        xlsx_column = first_value_column_indexlon_basso_dx, lat_basso_dx
        stack_year = stack[-8:-4]
        print 'stack_year:', stack_year
        # Devo creare i nuovi stack dal 1999 al 2018 dalla cartella nell'HD esterno: L2_Monitoraggio_Stack_Annuali_1999-2018?
        if 'LS8' in stack:
            SWIR2_band = 'band6' # LS8
            num_band = 7
        else:
            SWIR2_band = 'band7' # LS5/LS7
            num_band = 6
        # cropped_dataset_path è lo stack ritagliato sul poligono
        cropped_dataset_path, altezza_cropped_array, larghezza_cropped_array = mask_dataset(stack_dir_path + '/' + stack, polygon, dest_stack_cropped_dir)
        green_cropped_array, red_cropped_array, NIR_cropped_array, SWIR1_cropped_array, SWIR2_cropped_array = get_band_array(cropped_dataset_path, num_band, SWIR2_band)

        # Serve per il famoso controllo che vedrò più avanti
        MNDWI_cropped_array = (green_cropped_array - SWIR1_cropped_array)/(green_cropped_array + SWIR1_cropped_array)
        MNDWI_mean_value_listcropped_array_height.append(np.mean(MNDWI_cropped_array))

        geojson_name = os.path.basename(geojson_path)
        geojson_name = geojson_name[:geojson_name.index(".")]
        # Calcolo le statistiche su polygon. La funzione scrive i risultati relativi a un singolo anno
        calculate_stats(green_cropped_array, red_cropped_array, NIR_cropped_array, SWIR1_cropped_array, SWIR2_cropped_array, first_value_column_index, sheet_list)
        first_value_column_index += 1

    pixel_choice = False
    random_pixel_list = []
    first_value_column_index += 1

    # Scelgo un array che fa riferimento al geojson per ottenere le coordinate del punto (0,0)
    cropped_dataset = rasterio.open(cropped_dataset_path, 'r') # Mi serve l'oggetto dataset dello stack cropped
    lon_alto_sx, lat_alto_sx = cropped_dataset.xy(0,0) # Viene restituita una tupla del tipo (lon_00, lat_00). Controllare la shape
    lon_basso_dx, lat_basso_dx = cropped_dataset.xy(altezza_cropped_array - 1, larghezza_cropped_array - 1)
    cropped_dataset.close()

    # Con questo secondo ciclo calcolo le statistiche sui pixel di contorno estratti casualmente
    for stack in os.listdir(stack_dir_path):
        stack_year = stack[-8:-4]
        print stack_year
        if 'LS8' in stack:
            SWIR2_band = 'band6' # LS8
            num_band = 7
        else:
            SWIR2_band = 'band7' # LS5/LS7
            num_band = 6
        stack_path = stack_dir_path + '/' + stack
        # Scelgo i pixel in maniera casuale solo alla prima iterazione del ciclo. Per ora non mi interessa l'anno da cui prendo i pixel random.
        if pixel_choice is False:
            print 'Scelgo i pixel random'
            random_pixel_list = get_random_pixel(stack_dir_path, stack, lon_alto_sx, lat_alto_sx, lon_basso_dx, lat_basso_dx, altezza_cropped_array, larghezza_cropped_array, geojson_path, MNDWI_mean_value_list, num_band)
            pixel_choice = True
        green_array_bound, red_array_bound, NIR_array_bound, SWIR1_array_bound, SWIR2_array_bound = get_bound_array(stack_path, random_pixel_list, SWIR2_band, num_band)
        calculate_stats(green_array_bound, red_array_bound, NIR_array_bound, SWIR1_array_bound, SWIR2_array_bound, first_value_column_index, sheet_list)
        first_value_column_index += 1





# geojson = open(geojson_path, 'r').read()
# readable_json = json.loads(geojson)
# temp = readable_json['features'][0]['geometry']
# min_lon = temp['coordinates'][0][0][0]
# max_lat = 0.0
# for i in range(0, len(temp['coordinates'][0]) - 1): # L'ultimo elemento della lista corrisponde sempre al primo
#     if temp['coordinates'][0][i][0] <= min_lon:
#         min_lon = temp['coordinates'][0][i][0]
#         index_min_lon = i
#     if temp['coordinates'][0][i][1] > max_lat:
#         max_lat = temp['coordinates'][0][i][1]
#         index_max_lat = i
