#run this script in terminal or on virtual environment to download and transform DSS Foster Care data for Norfolk

import sys
import os

sys.path.append(os.getcwd())

from Preprocess import pre_process
from Batch_processing import batch_process
from Data_appendation import data_append_upload

def main():
    print("preprocessing images from Raw deployment images folder")
    pre_process()

    print("Running batch processing")
    batch_process()

    print("appending data and pushing data to dashboard")
    data_append_upload()

if __name__ == "__main__":
    main()