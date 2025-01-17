import os
import torch
import numpy as np
import random

from torchvision import transforms
from torch.utils.data import DataLoader
from config import Config
from utils.inference_process import ToTensor, Normalize, five_point_crop, sort_file
from data.pipal22_test import PIPAL22
from tqdm import tqdm
from glob import glob

os.environ['CUDA_VISIBLE_DEVICES'] = '0'


def setup_seed(seed):
    random.seed(seed)
    os.environ['PYTHONHASHSEED'] = str(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True


def eval_epoch(config, net, test_loader):
    with torch.no_grad():
        net.eval()
        name_list = []
        pred_list = []
        with open(config.valid_path + '/output.txt', 'w') as f:
            for data in tqdm(test_loader):
                pred = 0
                for i in range(config.num_avg_val):
                    x_d = data['d_img_org'].cuda()
                    x_d = five_point_crop(i, d_img=x_d, config=config)
                    pred += net(x_d)

                pred /= config.num_avg_val
                d_name = data['d_name']
                pred = pred.cpu().numpy()
                name_list.extend(d_name)
                pred_list.extend(pred)
            for i in range(len(name_list)):
                f.write(name_list[i] + ',' + str(pred_list[i]) + '\n')
            print(len(name_list))
        f.close()


def single_process(config):
    if not os.path.exists(config.valid):
        os.mkdir(config.valid)

    if not os.path.exists(config.valid_path):
        os.mkdir(config.valid_path)
    
    # data load
    test_dataset = PIPAL22(
        dis_path=config.test_dis_path,
        transform=transforms.Compose([Normalize(0.5, 0.5), ToTensor()]),
    )
    test_loader = DataLoader(
        dataset=test_dataset,
        batch_size=config.batch_size,
        num_workers=config.num_workers,
        drop_last=True,
        shuffle=False
    )
    net = torch.load(config.model_path)
    net = net.cuda()

    eval_epoch(config, net, test_loader)

    store_path = config.valid_path + '/output.txt'
    mean = sort_file(store_path)

    return mean




def run(input_dir):
    cpu_num = 1
    os.environ['OMP_NUM_THREADS'] = str(cpu_num)
    os.environ['OPENBLAS_NUM_THREADS'] = str(cpu_num)
    os.environ['MKL_NUM_THREADS'] = str(cpu_num)
    os.environ['VECLIB_MAXIMUM_THREADS'] = str(cpu_num)
    os.environ['NUMEXPR_NUM_THREADS'] = str(cpu_num)
    torch.set_num_threads(cpu_num)

    setup_seed(20)



    # config file
    config = Config({
        # dataset path
        "db_name": "PIPAL",
        "test_dis_path": input_dir,
        
        # optimization
        "batch_size": 10,
        "num_avg_val": 1,
        "crop_size": 224,   # 这个后面调整一下

        # device
        "num_workers": 8,

        # load & save checkpoint
        "valid": "./output/valid",
        "valid_path": "./output/valid/inference_valid",
        "model_path": "ckpt_valid"
    })


    score = single_process(config)

    return score

    

class video_scoring:
    def __init__(self) -> None:
        pass


    def run(self, input_folders = None, verbose=False): 
        print("This folder is ", input_folders)

        test_folders = glob(input_folders, recursive = True) # Need to have "/*"

        for input_dir in sorted(test_folders):
            score = run(input_dir)
            print(input_dir + " Average is " + str(score))
            


def main():
    scoring = video_scoring()
    scoring.run(input_folders = "/home/hikaridawn/Desktop/quality_proof_video/ESRGAN/V2/*", verbose = False)

if __name__ == "__main__":
    main()
    