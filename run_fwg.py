import os
import subprocess

epw_folder_path = "C:/Users/igorc/Desktop/Pre_Morphing"
jar_file_path = "C:/Users/igorc/Desktop/Pre_Morphing/FutureWeatherGenerator_v1.3.0.jar"

epw_files = [file for file in os.listdir() if file.endswith('.epw')]

for epw_file in epw_files:
    epw_file_path = os.path.join(epw_folder_path, epw_file)
    output_folder_path = os.path.join(epw_folder_path, "output/")

    print(epw_file_path)
    print(output_folder_path)

    command = [
        'java',
        '-cp',
        jar_file_path,
        'futureweathergenerator.Morph',
        epw_file_path,
        'BCC_CSM2_MR,CAS_ESM2_0,CMCC_ESM2,CNRM_CM6_1_HR,CNRM_ESM2_1,EC_Earth3,EC_Earth3_Veg,MIROC_ES2H,MIROC6,MRI_ESM2_0,UKESM1_0_LL',
        '1',
        '72',
        output_folder_path,
        'true',
        '0',
        'true'
    ]

    result = subprocess.run(command, capture_output=True, text=True)
    