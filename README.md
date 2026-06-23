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
|[2. Route Randomization and Selection]()|Creating and randomly selecting 0.75 mile long routes along street centerlines, to be traveled to collect data.|
|[3. ArcGIS Navigator]()|How to configure Navigator to the routes created, inside ArcGIS, for seemless turn-by-turn navigation.|
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
This module contains instructions on how to configure the routes generated in the last step to be used in [ArcGIS Navigator](https://www.google.com/url?sa=t&rct=j&q=&esrc=s&source=web&cd=&cad=rja&uact=8&ved=2ahUKEwi04cbwiZ6VAxV7K1kFHYhdJykQFnoECBsQAQ&url=https%3A%2F%2Fwww.esri.com%2Fen-us%2Farcgis%2Fproducts%2Farcgis-navigator%2Foverview&usg=AOvVaw2dK9R28XUZFK4B6tgYtLoX&opi=89978449). The routes are pulled into ArcGIS and using the [network analyst extension](https://www.google.com/url?sa=t&rct=j&q=&esrc=s&source=web&cd=&cad=rja&uact=8&ved=2ahUKEwiy19ilip6VAxXfGVkFHY97K78QFnoECA0QAQ&url=https%3A%2F%2Fdoc.esri.com%2Fen%2Farcgis-pro%2Flatest%2Fhelp%2Fanalysis%2Fnetworks%2Fwhat-is-network-analyst-.html&usg=AOvVaw11x_Ct30civ-mSXeF9islQ&opi=89978449) and [AGOL](https://www.google.com/url?sa=t&rct=j&q=&esrc=s&source=web&cd=&cad=rja&uact=8&ved=2ahUKEwiR7oi8ip6VAxVRKlkFHZDXA3EQFnoECBsQAQ&url=https%3A%2F%2Fwww.arcgis.com%2F&usg=AOvVaw0LxRz3vzchopucVMCyvM6E&opi=89978449) you can run the public map to ArcGIS Navigator which can be access by the end-user to navigate the routes generated in the previous step. This step used to be accomplished on paper which made it less than ideal for real-time navigation of routes.

## 4. Route Navigation and Data Collection
This module is more of an instruction manual versus a traditional repo folder. It provides detailed instructions on how to actual drive to capture data, camera configuration, Route Navigation, and edge-case handling.

##5. Image and Data Preprocessing
Once images have been captured on ranndomized routes, these images and their associated metadata must be preprocessed. The script in this module ensures GPS, and time data are extracted from images to be carried over into the final results for analysis and viewing of datapoints on a map and overtime. The second reason this script runs is to get images ready for model inferencing. a few key visual tranformations are applied to the images before inferencing to improve model performance.
 

# Build and Test
TODO: Describe and show how to build your code and run the tests. 

# Contribute
TODO: Explain how other users and developers can contribute to make your code better. 

If you want to learn more about creating good readme files then refer the following [guidelines](https://docs.microsoft.com/en-us/azure/devops/repos/git/create-a-readme?view=azure-devops). You can also seek inspiration from the below readme files:
- [ASP.NET Core](https://github.com/aspnet/Home)
- [Visual Studio Code](https://github.com/Microsoft/vscode)
- [Chakra Core](https://github.com/Microsoft/ChakraCore)