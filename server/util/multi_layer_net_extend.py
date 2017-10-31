# coding: utf-8
#
# This script is based on https://github.com/oreilly-japan/deep-learning-from-scratch
#

import sys
import os
import numpy as np
from collections import OrderedDict
from util.utils import *


class MultiLayerNetExtend:

    def __init__(self, input_size, hidden_size_list, output_size, weight_decay_lambda=0.00001, dropout_ration = 0.5):
        self.input_size = input_size
        self.output_size = output_size
        self.hidden_size_list = hidden_size_list
        self.hidden_layer_num = len(hidden_size_list)
        self.weight_decay_lambda = weight_decay_lambda
        self.params = {}

        self.__init_weight()
        self.layers = OrderedDict()

        for idx in range(1, self.hidden_layer_num + 1):
            self.layers['Affine' + str(idx)] = Affine(self.params['W' + str(idx)],
                                                      self.params['b' + str(idx)])
            self.params['gamma' + str(idx)] = np.ones(hidden_size_list[idx - 1])
            self.params['beta' + str(idx)] = np.zeros(hidden_size_list[idx - 1])
            self.layers['BatchNorm' + str(idx)] = BatchNormalization(self.params['gamma' + str(idx)],
                                                                     self.params['beta' + str(idx)])
            self.layers['Activation_function' + str(idx)] = Relu()
            self.layers['Dropout' + str(idx)] = Dropout(dropout_ration - (0.1 * idx))

        idx = self.hidden_layer_num + 1
        self.layers['Affine' + str(idx)] = Affine(self.params['W' + str(idx)], self.params['b' + str(idx)])

        self.last_layer = SoftmaxWithLoss()

    def __init_weight(self):
        all_size_list = [self.input_size] + \
            self.hidden_size_list + [self.output_size]
        for idx in range(1, len(all_size_list)):
            scale = np.sqrt(2.0 / all_size_list[idx - 1])
            self.params['W' + str(idx)] = scale * \
                np.random.randn(all_size_list[idx - 1], all_size_list[idx])
            self.params['b' + str(idx)] = np.zeros(all_size_list[idx])

    def predict(self, x, train_flg=False):
        for key, layer in self.layers.items():
            if "BatchNorm" in key:
                x = layer.forward(x, train_flg)
            else:
                x = layer.forward(x)

        return x

    def loss(self, x, t, train_flg=False):
        y = self.predict(x, train_flg)

        weight_decay = 0
        for idx in range(1, self.hidden_layer_num + 2):
            W = self.params['W' + str(idx)]
            weight_decay += 0.5 * self.weight_decay_lambda * np.sum(W**2)

        return self.last_layer.forward(y, t) + weight_decay

    def check(self, X, T):
        Y = self.predict(X, train_flg=False)
        Y = np.argmax(Y, axis=1)
        if T.ndim != 1:
            T = np.argmax(T, axis=1)

        accuracy = np.sum(Y == T) / float(X.shape[0])

        j = 0
        tp = 0
        sp = 0
        ap = 0
        for y in Y:
            if y == 1:
                sp += 1
                if T[j] == 1:
                    tp += 1
            if T[j] == 1:
                ap += 1
            j += 1

        try:
            precision = tp/sp
            recall = tp/ap
        except ZeroDivisionError:
            precision = 0
            recall = 0

        return accuracy, precision, recall

    def answer(self, X):
        Y = self.predict(X, train_flg=False)
        Y = np.argmax(Y, axis=1)

        return Y

    def gradient(self, x, t):
        # forward
        self.loss(x, t, train_flg=True)

        # backward
        dout = 1
        dout = self.last_layer.backward(dout)

        layers = list(self.layers.values())
        layers.reverse()
        for layer in layers:
            dout = layer.backward(dout)

        # Setting
        grads = {}
        for idx in range(1, self.hidden_layer_num + 2):
            grads['W' + str(idx)] = self.layers['Affine' + str(idx)].dW + \
                self.weight_decay_lambda * self.params['W' + str(idx)]
            grads['b' + str(idx)] = self.layers['Affine' + str(idx)].db

            if idx != self.hidden_layer_num + 1:
                grads['gamma' + str(idx)] = self.layers['BatchNorm' + str(idx)].dgamma
                grads['beta' + str(idx)] = self.layers['BatchNorm' + str(idx)].dbeta

        return grads
