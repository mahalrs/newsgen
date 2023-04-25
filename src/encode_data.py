# Copyright 2023 The Newsgen Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import argparse
import json
import os
import numpy as np
import torch
from PIL import Image
from newsgen.tokenizer import NewsgenTokenizer

parser = argparse.ArgumentParser()
parser.add_argument('--dataset',
                    default='data/visual_news_mini',
                    help='Directory containing VisualNews dataset')


device = 'cuda' if torch.cuda.is_available() else 'cpu'
tok = NewsgenTokenizer('../src/pretrained/exp1.ckpt', device)

def encode(dataset_dir, file_name):
    with open(os.path.join(dataset_dir, file_name), 'r') as f:
        data = json.load(f)
        for split in ['train', 'val', 'test']:
            for i in range(0, len(data[split]), 4):
                story_batch = data[split][i:i+4]
                headline_batch = []
                caption_batch = []
                image_batch = []
                
                for story in story_batch:
                    del story["topic"] 
                    del story["source"]
                    del story["article_path"]
                    
                    if 'headline' in story:
                        headline_batch.append(story['headline'])
                    caption_batch.append(story['caption'])
                    image_path = os.path.join(dataset_dir, story['image_path'][2:])
                    img = Image.open(image_path).convert('RGB')
                    image_batch.append(img)
                
                if len(headline_batch) > 0:
                    headline_encoding = tok.encode_text_batch(headline_batch)['input_ids']
                caption_encoding = tok.encode_text_batch(caption_batch)['input_ids']
                image_encoding = tok.encode_image_batch(image_batch)
                
                for j in range(len(story_batch)):
                    story = story_batch[j]
                    if len(headline_batch) > 0:
                        story['headline_tokens'] = headline_encoding[j].tolist()
                    story['caption_tokens'] = caption_encoding[j].tolist()
                    story['image_tokens'] = image_encoding[j].tolist()
                
        with open(os.path.join(dataset_dir, f"{file_name[:-5]}_encoding.json"), 'w') as f:
            json.dump(data, f)

def main():
    args = parser.parse_args()
    dataset_dir = args.dataset

    torch.set_grad_enabled(False)
    
    encode(dataset_dir, 'headlines.json')
    print("headlines.json encoded")
    encode(dataset_dir, 'captions.json')
    print("captions.json encoded")

if __name__ == '__main__':
    main()