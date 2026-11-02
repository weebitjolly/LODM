# Litter Object Detection Model (LODM)
Welcome to the City of Norfolk's Litter Object Detection Model (LODM) Repo!

This Repository contains the data and software necessary to get the LODM system started, accompanied by the products and data that have come as a result of the deployment of this Model

LODM is a comprehensive, end-to-end computer vision pipeline that utilizes [YOLO](https://www.google.com/url?sa=t&rct=j&q=&esrc=s&source=web&cd=&cad=rja&uact=8&ved=2ahUKEwj70amp052VAxWPFVkFHRjaNAEQFnoECEIQAQ&url=https%3A%2F%2Farxiv.org%2Fabs%2F1506.02640&usg=AOvVaw017FtXr2m7HO50_HFP3dAZ&opi=89978449), Python, and GIS software and techniques, to capture when, where and how much litter is present in the City of Norfolk. This project successfully quantifies litter levels in the City helping to inform targetted clean-up efforts across the City, beautifying the City and therefore increasing the propensity of residents to contribute to the economic activity of the City. This project is an effort led by [Keep Norfolk Beautiful(KNB)](https://www.norfolk.gov/6308/Keep-Norfolk-Beautiful) in collaboration with [CivicLab](https://www.norfolk.gov/4803/CivicLab-Norfolk).

If you are interested in volunteering to help keep norfolk beautiful click this [link](https://www.norfolk.gov/FormCenter/Keep-Norfolk-Beautiful-35/Volunteer-Interest-Form-685)

If you have any questions about the software or techniques found in this repo please click this [link](mailto:Nicholas.darrow@norfolk.gov).

# Table of Contents
| Module | Summary |
|--------|---------|
|[1. Route Navigation and Data Collection](https://dev.azure.com/City-of-Norfolk/LODM/_git/LODM%20Production?path=/Route%20Navigation%20and%20Data%20Collection&version=GBmain)|Provides instructions on how to use the application, the GoPro, and how to drive for this process|
|[2. Image and Data Preprocessing](https://dev.azure.com/City-of-Norfolk/LODM/_git/LODM%20Production?path=/Image%20and%20Data%20Preprocessing&version=GBmain)|Once data is captured run this script to prepare images and image metadata to be inferenced by the model|
|[3. Batch Processing](https://dev.azure.com/City-of-Norfolk/LODM/_git/LODM%20Production?path=/Batch%20Processing&version=GBmain)|Run after preprocessing data to get results|
|[4. Data Appendation and Dashboard](https://dev.azure.com/City-of-Norfolk/LODM/_git/LODM%20Production?path=/Data%20Appendation%20and%20Dashboard&version=GBmain)|Script that appends new data to the old data and runs that data to the powerbi dashboard that visualizes results|

# Getting Started
You can start by navigating each of the modules above if you want a more in-depth explanation of each step of this project. These modules serve as the instruction manual for recreating this project for your own city. below you'll find a short synopsis of each step.

## 1. Route Navigation and Data Collection
This module is more of an instruction manual versus a traditional repo folder. It provides detailed instructions on how to actual drive to capture data, camera configuration, Route Navigation, and edge-case handling.

## 2. Image and Data Preprocessing
Once images have been captured on ranndomized routes, these images and their associated metadata must be preprocessed. The script in this module ensures GPS, and time data are extracted from images to be carried over into the final results for analysis and viewing of datapoints on a map and overtime. The second reason this script runs is to get images ready for model inferencing. a few key visual tranformations are applied to the images before inferencing to improve model performance. Finally, the photos are also cropped to remove tree and horizonlines as there is no litter in the sky, and duplicate images such as those taken at stops are removed based on how geographically close they are using their lat and long measures.

## 3. Batch Processing
After having images and accompanying metadata handled, they are then passed through a batch processing script that outputs inference results for batches of photos and metadata. The output contains a structured csv that contains attributes such as time and GPS data, with raw counts and litter level by route based on the cumulative distance of each route. Norfolk wards are geocoded to appropriate coordinates, and any data points that do not contain metadata are removed.

## 4. Data Appendation and Dashboard
Once the results are made available for a deployment, the data is appended to existing data in the home directory. You can then pull this data into an application such as PowerBI, Tableau, R or Python for visualization purposes to more easily understand location and temporal trends of litter levels and counts.

# Quick start

## For KNB
To begin you'll start by following the Route Directions and Litter Survey Standard Operating Procedures. You will drive with the GoPro attached to a city vehicle along those pre-determined routes following the documents' directions as closely as possible. These can be found in the [1. Route Navigation and Data Collection](https://dev.azure.com/City-of-Norfolk/LODM/_git/LODM%20Production?path=/Route%20Navigation%20and%20Data%20Collection&version=GBLODM_Forever) folder of this repository.

Once these routes have been driven and data collected, KNB will physically hand off the sd card containing the image data to an approved CivicLab team member

## For CivicLab
This section is written for the CivicLab team member responsible for running the pipeline on the backend.

### What you need 
| **Python 3.11+** | For running main.py which runs all of the processing scripts sequentially |
| **Virtual Environment** | depending on where you are running this a virtual environment will allow all of the packages in the requirements file to download and import for proper execution|

## 1. Folder Creation
Start by first creating a folder in "C:\Litter Production\Deployments" titled "deployment_#" with the # being the number deployment you are on, (the last deployment was 4, so the last folder was titled "deployment_4") this folder will be referenced by the pipeline. Once this is created, create another folder within that one called "Raw Deployment Images" like so: "C:\Litter Production\Deployments\deployment_3\Raw Deployment Images".

## 2. Data Upload
Plug in the GoPro with the SD from KNB insert and plug the camera turned-on into the data science computer via USB-C. Once connected navigate to the GoPro's image folders here: "This PC\HERO13 Black\GoPro MTP Client Disk Volume\DCIM". From here export all valid .jpg files from each of the GoPro's image folders to the "Raw Deployment Images" folder in the C:drive. There will more than likely be multiple folders inside the GoPro with images. Take a passing check to ensure that the files you are sending are only jpg's and that each file is taken of the street any other photos should be discarded. There is no need to keep any of the images on the GoPro so cut and paste over. This will take some time.

## 3. Run Main
Once all files are moved to the Raw Deployment Images folder inside the most recent deployment folder. run the "main.py" script here: "C:\Litter Production\Pipeline\LODM%20Production\Scripts\main.py" by running:

```python
python "C:\Litter Production\Pipeline\LODM%20Production\Scripts\main.py"
```

This will take an hour or so and inform when each script has completed in the terminal

## 4. Finishing up
Once this is done running, the data will automatically feed to the dashboard. 

## Notes
The results feed to a local directory, you will need to declare where you want results to go.

for the purposes of this repo, all training data and data collected for results are not included. The model used in detection is available along with the script used to train the model on google colab.



