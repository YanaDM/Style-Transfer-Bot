from PIL import Image
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
import torchvision.transforms as transforms
import torchvision.models as models 
from scipy import misc # required version of scipy is 1.2.0
from transformer_net import TransformerNet
import re
import os

# В данном классе мы хотим полностью производить всю обработку картинок, которые поступают к нам из телеграма.
class StyleTransferModel:
    def transfer_style(self, content_img_stream, model_name):
        device = torch.device("cpu")

        content_image = self.process_image(content_img_stream)

        with torch.no_grad():
            style_model = TransformerNet()
            # ниже нужно указать путь до папки, где хранятся модели
            # base_dir = './saved_models/'
            base_dir = '/Users/yanadm/Documents/Style Transfer Bot/saved_models/'
            filename = model_name
            path_to_model = os.path.join(base_dir, filename)
            state_dict = torch.load(path_to_model)
            for k in list(state_dict.keys()):
                if re.search(r'in\d+\.running_(mean|var)$', k):
                    del state_dict[k]
            style_model.load_state_dict(state_dict)
            style_model.to(device)
            output = style_model(content_image).cpu()    
        return misc.toimage(output[0])
    # Обработка изображения
    def process_image(self, img_stream):
        imsize = 512
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        loader = transforms.Compose([
            transforms.Resize(imsize),  # нормируем размер изображения
            transforms.CenterCrop(imsize),
            transforms.ToTensor()])  # превращаем в удобный формат

        image = Image.open(img_stream)
        image = loader(image).unsqueeze(0)
        return image.to(device, torch.float)
