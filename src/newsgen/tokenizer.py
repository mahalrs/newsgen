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

import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))

import torch

from torchvision import transforms
from transformers import BartTokenizer

from vqgan.model import VQModel


class NewsgenTokenizer():

    def __init__(self, vqgan_ckpt_path, hparams=dict(), device=None):
        self.device = device

        self.vqgan = VQModel.load_from_checkpoint(vqgan_ckpt_path, **hparams)
        if device:
            self.vqgan.to(device)
        for param in self.vqgan.parameters():
            param.requires_grad = False
        self.vqgan.eval()

        self.tokenizer = BartTokenizer.from_pretrained('facebook/bart-large')

        self.transform = transforms.Compose([
            transforms.Resize((256, 256)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.5, 0.5, 0.5], std=[0.5, 0.5, 0.5])
        ])

        self.ignore_tokens = [
            16384,  # decoder start token
            16385,  # bos token
            16386,  # eos token
            16387,  # pad token
        ]

    def encode_text(self, inp):
        return self.tokenizer(inp,
                              max_length=1024,
                              padding='max_length',
                              truncation=True,
                              return_tensors='pt')

    def encode_text_batch(self, inputs):
        return self.tokenizer.batch_encode_plus(inputs,
                                                max_length=1024,
                                                padding='max_length',
                                                truncation=True,
                                                return_tensors='pt')

    def encode_image(self, image):
        img = self.transform(image).unsqueeze(0)
        if self.device:
            img = img.to(self.device)

        with torch.no_grad():
            _, _, info = self.vqgan.encode(img)
            return info[2]

    def encode_image_batch(self, images):
        imgs = torch.stack([self.transform(img) for img in images])
        if self.device:
            imgs = imgs.to(self.device)

        with torch.no_grad():
            _, _, info = self.vqgan.encode(imgs)

            return info[2].reshape(-1, 256)

    def decode_images(self, logits):
        if self.device:
            logits = logits.to(self.device)

        # Apply a softmax activation function to the logits tensor
        probs = torch.softmax(logits, dim=-1)

        # Create a mask to ignore special tokens
        mask = torch.zeros_like(probs)
        for token in self.ignore_tokens:
            mask[:, :, token] = -float('inf')

        # Apply the mask to the probabilities
        probs = probs + mask

        # Take the index of the maximum value in each probability distribution
        indices = torch.argmax(probs, dim=-1)[:, :-1]

        with torch.no_grad():
            return self.vqgan.decode_code(indices)

    def get_indices(self, logits):
        if self.device:
            logits = logits.to(self.device)

        # Apply a softmax activation function to the logits tensor
        probs = torch.softmax(logits, dim=-1)

        # Create a mask to ignore special tokens
        mask = torch.zeros_like(probs)
        for token in self.ignore_tokens:
            mask[:, :, token] = -float('inf')

        # Apply the mask to the probabilities
        probs = probs + mask

        # Take the index of the maximum value in each probability distribution
        indices = torch.argmax(probs, dim=-1)[:, :-1]

        return indices

    def decode_images_code(self, indices):
        if self.device:
            indices = indices.to(self.device)

        # Remove BOS token
        if indices.shape[1] == 257:
            indices = indices[:, 1:]

        with torch.no_grad():
            return self.vqgan.decode_code(indices)
