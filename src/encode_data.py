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
import torch

from PIL import Image
from tqdm import tqdm

from newsgen.tokenizer import NewsgenTokenizer

parser = argparse.ArgumentParser()
parser.add_argument('--dataset',
                    default='./data/visual_news_mini',
                    help='Directory containing VisualNews dataset')
parser.add_argument('--vqgan_ckpt',
                    default='./pretrained/vqgan.ckpt',
                    help='Path to VQGAN checkpoint')


def encode(dataset_dir, file_name, tok):
    with open(os.path.join(dataset_dir, file_name), 'r') as f:
        data = json.load(f)

    pbar = tqdm(total=len(data['train']) + len(data['val']) + len(data['test']))

    for split in ['train', 'val', 'test']:
        for i in range(0, len(data[split]), 4):
            story_batch = data[split][i:i + 4]
            headline_batch = []
            caption_batch = []
            image_batch = []

            for story in story_batch:
                del story['topic']
                del story['source']
                del story['article_path']

                if 'headline' in story:
                    headline_batch.append(story['headline'])
                caption_batch.append(story['caption'])
                image_path = os.path.join(dataset_dir, story['image_path'][2:])
                img = Image.open(image_path).convert('RGB')
                image_batch.append(img)

            if len(headline_batch) > 0:
                headline_encoding = tok.encode_text_batch(headline_batch).to(
                    'cpu')
                headline_tokens = headline_encoding['input_ids']
                headline_attention = headline_encoding['attention_mask']
            caption_encoding = tok.encode_text_batch(caption_batch).to('cpu')
            caption_tokens = caption_encoding['input_ids']
            caption_attention = caption_encoding['attention_mask']
            image_encoding = tok.encode_image_batch(image_batch).to('cpu')

            for j in range(len(story_batch)):
                story = story_batch[j]
                if len(headline_batch) > 0:
                    story['headline_tokens'] = headline_tokens[j].tolist()
                    story['headline_attention'] = headline_attention[j].tolist()
                story['caption_tokens'] = caption_tokens[j].tolist()
                story['caption_attention'] = caption_attention[j].tolist()
                story['image_tokens'] = image_encoding[j].tolist()

            pbar.update(4)
    pbar.close()

    with open(os.path.join(dataset_dir, f'encoded_{file_name}'), 'w') as f:
        json.dump(data, f)


def main():
    args = parser.parse_args()
    dataset_dir = args.dataset
    assert os.path.exists(dataset_dir), f'{dataset_dir} does not exist.'
    assert os.path.isdir(dataset_dir), f'{dataset_dir} is not a directory.'

    ckpt_path = args.vqgan_ckpt
    assert os.path.exists(ckpt_path), f'{ckpt_path} does not exist.'
    assert os.path.isfile(ckpt_path), f'{ckpt_path} is not a file.'

    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    tok = NewsgenTokenizer(ckpt_path, device)

    print('Encoding headlines.json')
    encode(dataset_dir, 'headlines.json', tok)
    print('Encoding captions.json')
    encode(dataset_dir, 'captions.json', tok)


if __name__ == '__main__':
    main()
