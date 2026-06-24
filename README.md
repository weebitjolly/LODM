# Litter Object Detection Model (LODM)
Welcome to the City of Norfolk's Litter Object Detection Model (LODM) Repo!

This Repository contains the data and software necessary to get the LODM system started, accompanied by the products and data that have come as a result of the deployment of this Model

LODM is a comprehensive, end-to-end computer vision pipeline that utilizes [YOLO](https://www.google.com/url?sa=t&rct=j&q=&esrc=s&source=web&cd=&cad=rja&uact=8&ved=2ahUKEwj70amp052VAxWPFVkFHRjaNAEQFnoECEIQAQ&url=https%3A%2F%2Farxiv.org%2Fabs%2F1506.02640&usg=AOvVaw017FtXr2m7HO50_HFP3dAZ&opi=89978449), Python, and GIS software and techniques, to capture when, where and how much litter is present in the City of Norfolk. This project successfully quantifies litter levels in the City helping to inform targetted clean-up efforts across the City, beautifying the City and therefore increasing the propensity of residents to contribute to the economic activity of the City. This project is an effort led by [Keep Norfolk Beautiful(KNB)](https://www.norfolk.gov/6308/Keep-Norfolk-Beautiful) in collaboration with [CivicLab](https://www.norfolk.gov/4803/CivicLab-Norfolk).

If you are interested in volunteering to help keep norfolk beautiful click this [link](https://www.norfolk.gov/FormCenter/Keep-Norfolk-Beautiful-35/Volunteer-Interest-Form-685)

If you have any questions about the software or techniques found in this repo please click this [link](mailto:Nicholas.darrow@norfolk.gov).

#Table of Contents
| Module | Summary |
|--------|---------|
|[1. Model Training and Evaluation](https://dev.azure.com/City-of-Norfolk/LODM/_git/LODM%20Production?path=/Model%20Training%20and%20Evaluation&version=GBmain)|How to get the model trained and evaluated, including the data it is trained on.|
|[2. Route Randomization and Selection](https://dev.azure.com/City-of-Norfolk/LODM/_git/LODM%20Production?path=/Route%20Randomization%20and%20Selection&version=GBmain)|Creating and randomly selecting 0.75 mile long routes along street centerlines, to be traveled to collect data.|
|[3. ArcGIS Navigator](https://dev.azure.com/City-of-Norfolk/LODM/_git/LODM%20Production?path=/ArcGIS%20Navigator&version=GBmain)|How to configure Navigator to the routes created, inside ArcGIS, for seemless turn-by-turn navigation.|
|[4. Route Navigation and Data Collection]()|Provides instructions on how to use the application, the GoPro, and how to drive for this process|
|[5. Image and Data Preprocessing]()|Once data is captured run this script to prepare images and image metadata to be inferenced by the model|
|[6. Batch Processing]()|Run after preprocessing data to get results|
|[7. Data Appendation and Dashboard]()|Script that appends new data to the old data and runs that data to the powerbi dashboard that visualizes results|


# Getting Started
You can start by navigating each of the modules above if you want a more in-depth explanation of each step of this project. These modules serve as the instruction manual for recreating this project for your own city. below you'll find a short synopsis of each step.

## 1. Model Training and Evaluation
This module contains information about how to get this model up and running off the ground. This model is trained to find individual pieces of litter or large groupings of litter as a litter object. It is trained on over 10,000 images of litter ranging in contexts from aquatic, streetscape, suburban to nature. This module starts from data collection, to setting up the yaml file, configuring model hyperparameters, and validating the model.

## 2. Route Randomization and Selection
This module provides the script and instructions for how to randomly select routes for a deployment. A deployment is anytime KNB and/or CivicLab has or will travel across the streets of Norfolk and capture images of streetscapes, curbs and sidewalks. Before travelling to capture images, routes that will be travelled must be selected. These routes are randomly selected to ensure an equal distribution of what is essentially a litter survey of the City of Norfolk. It would be unfair to just survey areas that contain higher expected average litter levels. This module ensures the routes surveyed are equal distance and randomly geographically distributed across Norfolk.

## 3. ArcGIS Navigator
This module contains the geodatabase used that uses routes generated in the last step to be used in [ArcGIS Navigator](https://www.google.com/url?sa=t&rct=j&q=&esrc=s&source=web&cd=&cad=rja&uact=8&ved=2ahUKEwi04cbwiZ6VAxV7K1kFHYhdJykQFnoECBsQAQ&url=https%3A%2F%2Fwww.esri.com%2Fen-us%2Farcgis%2Fproducts%2Farcgis-navigator%2Foverview&usg=AOvVaw2dK9R28XUZFK4B6tgYtLoX&opi=89978449). The routes are pulled into ArcGIS and using the [network analyst extension](https://www.google.com/url?sa=t&rct=j&q=&esrc=s&source=web&cd=&cad=rja&uact=8&ved=2ahUKEwiy19ilip6VAxXfGVkFHY97K78QFnoECA0QAQ&url=https%3A%2F%2Fdoc.esri.com%2Fen%2Farcgis-pro%2Flatest%2Fhelp%2Fanalysis%2Fnetworks%2Fwhat-is-network-analyst-.html&usg=AOvVaw11x_Ct30civ-mSXeF9islQ&opi=89978449) and [AGOL](https://www.google.com/url?sa=t&rct=j&q=&esrc=s&source=web&cd=&cad=rja&uact=8&ved=2ahUKEwiR7oi8ip6VAxVRKlkFHZDXA3EQFnoECBsQAQ&url=https%3A%2F%2Fwww.arcgis.com%2F&usg=AOvVaw0LxRz3vzchopucVMCyvM6E&opi=89978449) you can run the public map to ArcGIS Navigator which can be access by the end-user to navigate the routes generated in the previous step. This step used to be accomplished on paper which made it less than ideal for real-time navigation of routes.

## 4. Route Navigation and Data Collection
This module is more of an instruction manual versus a traditional repo folder. It provides detailed instructions on how to actual drive to capture data, camera configuration, Route Navigation, and edge-case handling.

## 5. Image and Data Preprocessing
Once images have been captured on ranndomized routes, these images and their associated metadata must be preprocessed. The script in this module ensures GPS, and time data are extracted from images to be carried over into the final results for analysis and viewing of datapoints on a map and overtime. The second reason this script runs is to get images ready for model inferencing. a few key visual tranformations are applied to the images before inferencing to improve model performance. Finally, the photos are also cropped to remove tree and horizonlines as there is no litter in the sky, and duplicate images such as those taken at stops are removed based on how geographically close they are using their lat and long measures.

## 6. Batch Processing
After having images and accompanying metadata handled, they are then passed through a batch processing script that outputs inference results for batches of photos and metadata. The output contains a structured csv that contains attributes such as time and GPS data, with raw counts and litter level by route based on the cumulative distance of each route. Norfolk wards are geocoded to appropriate coordinates, and any data points that do not contain metadata are removed.

## 7. Data Appendation and Dashboard
Once the results are made available for a deployment, the data is appended to existing data in the home directory. You can then pull this data into an application such as PowerBI, Tableau, R or Python for visualization purposes to more easily understand location and temporal trends of litter levels and counts. 

# Build and Test

##1.
To begin building this project, begin at module 1 by downloading the jupyter notebook and train the model with data stored on azure blob storage.

##2.
Move to module 2 and run the script in that module. You will need to download the City of Norfolk Street centerlines geodatabase and the wards.shp file. you can use your own cities streetline GDB and ward, civic league or the governmental dilineation that you choose.

##3.
after creating the routes bring them into ArcGIS and configure them for Navigator. Please reference the RouteRandomizer Geodatabase for examples.

##4.
You can reference the documents in module 4 to follow the proper procedures and rules to capture data.

##5.
Use the python file after you have configure your directories properly following collection of the data. Executing this file will properly preprocess your images and accompanying metadata. for batch processing in the next module. 

##6.
You may use the model you trained or the model in module 6 for batch processing

##7.
run the litter data appendation script to append to existing data from prior deployments.

# Future Improvements
This section goes over possible improvements to this project and the processes included in it. This section will generally follow the pipeline's flow

## -Improved and Specialized model 
Currently the model is trained on non-proprietary data sourced from [Roboflow Universe](https://universe.roboflow.com/), which is unfortunately unavailable on the website anymore. The data contains images of varying quality across different environments and has been verified for quality, to the best of our abilities, but there was room for redundant or poor quality data that snuck through the cracks. Not only that the image data was not sourced from Norfolk, meaning that the model is trained to find litter across any environment, which is a benefit in itself as it allows for reproducibility in other cities and environments, but leaves room for error in specialized use-cases such as Norfolk's streetscapes. 

We have included a capacity to retrain this model with data that is collected during deployments as the current pipelines saves images and accompanying annotations. One could collect a corpora of annotated image data from deployments and retrain this model for specific use in their own context. That being said, a large amount of data must be captured to accomplish this, upwards of 10,000 images that match the project owner's use-case.

## -Previous Route Selection and Route History
In the current pipeline routes are randomly selected for equality of geographic distribution, but it does not save previous routes. This makes it impossible to conduct continued analysis of a single location to see how that locations differs in litter levels and count overtime with targetted clean-up efforts. In the future we want to add a functionality to the pipeline and navigator that allows users to choose from previously created and surveyed routes so that continually analysis can be conducted on those spots.

## -ArcGIS Navigator and Navigation optimization
ArcGIS Navigator like any navigating software has it's quirks. Using the network analyst extension in ArcGIS, the map layer must be configured for the app and then published to AGOL for the App to pull in. Currently it works as expected, but its not fully fleshed out. It needs to e further developed.

## -Norfolk Open Data Portal Data Hosting
[The Norfolk Open Data Portal](https://data.norfolk.gov/) is a public resource for hosting Norfolk's data about City programs, intitives and others figures, statistics and facts about Norfolk. In the future we will run deployment results to the Norfolk open data portal for users of the portal to use and pull this data.
## -Pipeline integrated into a cloud framework for greater automation and optimization
currently this process runs locally on a virtual environment and requires heavy input by the administrator. This process will be moved to azure in the future and include a UI that KNB, our stakeholder can use to choose routes, upload images and automatically recieve results that will be uploaded to the Norfolk Open Data Portal.

### Disclaimer
This project is by no means a final project and is iteratively being improved and tested upon. The code and data in this repository is experimental, and should be individually verified and iterated upon in production environments.