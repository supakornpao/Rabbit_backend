import os
import logging
import json
import numpy
import joblib

import io
import torch
import torch.nn as nn
import torch.quantization # Import the quantization library
import torchvision.models as models
import torchvision.transforms as transforms
from PIL import Image
import numpy as np


from collections import OrderedDict

def init():
    """
    This function is called when the container is initialized/started, typically after create/update of the deployment.
    You can write the logic here to perform init operations like caching the model in memory
    """
    global quantized_model
    # AZUREML_MODEL_DIR is an environment variable created during deployment.
    # It is the path to the model folder (./azureml-models/$MODEL_NAME/$VERSION)
    # Please provide your model's folder name if there is one

    model = models.densenet121(weights=None)
    num_ftrs = model.classifier.in_features
    model.classifier = nn.Linear(num_ftrs, 3)  # 3 classes: Normal, Nevus, Melanoma
    
    model_path = os.path.join(os.getenv("AZUREML_MODEL_DIR"), "testCancer/DenseNetModelV5_3.pth")
    checkpoint = torch.load(model_path, map_location=torch.device('cpu'))
    state_dict = checkpoint['model_state_dict']
    new_state_dict = OrderedDict((k[6:] if k.startswith('model.') else k, v) for k, v in state_dict.items())
    model.load_state_dict(new_state_dict)
    model.eval()
    quantized_model = torch.quantization.quantize_dynamic(
        model, {torch.nn.Linear}, dtype=torch.qint8
    )
    logging.info("Init complete")




preprocess = transforms.Compose([
    transforms.Resize((450, 450)),
    transforms.ToTensor(),
])

lesion_map = {
    0: 'Normal',
    1: 'Nevus',
    2: 'Melanoma',
}

def transform_image(image_bytes):
    image = Image.fromarray(image_bytes)
    return preprocess(image).unsqueeze(0)

def get_prediction(tensor):
    with torch.no_grad():
        # Use the faster QUANTIZED model for inference
        output = quantized_model(tensor)
        probs = torch.nn.functional.softmax(output[0], dim=0)
        idx = probs.argmax().item()
        confidence = probs[idx].item()
        return lesion_map.get(idx, 'Unknown'), confidence

def run(raw_data):
    """
    This function is called for every invocation of the endpoint to perform the actual scoring/prediction.
    In the example we extract the data from the json input and call the scikit-learn model's predict()
    method and return the result back
    """
    try:
        logging.info("model 1: request received")
        if isinstance(raw_data, str):
            json_data = json.loads(raw_data)
        else:
            json_data = raw_data
            
        # If the result is still a string (Double Encoding), load it one more time
        if isinstance(json_data, str):
            json_data = json.loads(json_data)

        # Now accessing ["data"] will not throw a string index error
        data = json_data["data"]

        #convert list back to np.array
        img_array = np.array(data).astype('uint8')
        img_array = np.squeeze(img_array)
        tensor = transform_image(img_array)
        label, confidence = get_prediction(tensor)
        confidence = round(confidence * 100, 2)
        logging.info("Request processed")
        return json.dumps({"result": f"{label}: {confidence}%"})
    except Exception as e:
        return json.dumps({"error":str(e)})

    