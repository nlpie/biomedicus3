# Copyright 2019 Regents of the University of Minnesota.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from argparse import ArgumentParser
from pathlib import Path, PurePath

from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint, TensorBoard
from time import time

from biomedicus.sentences.data import train_validation


def training_parser():
    parser = ArgumentParser(add_help=False)
    parser.add_argument('--epochs', type=int, default=100,
                        help="number of epochs to run training.")
    parser.add_argument('--tensorboard', action='store_true', default=False,
                        help="whether to use a keras.callbacks.TensorBoard.")
    parser.add_argument('--checkpoints', type=bool, default=True,
                        help="whether to save the best model during training.")
    parser.add_argument('--early-stopping', type=bool, default=True,
                        help="whether to stop when the model stops improving.")
    parser.add_argument('--early-stopping-patience', type=int, default=5,
                        help="how many epochs without improvement before stopping.")
    parser.add_argument('--early-stopping-delta', type=float, default=0.0001,
                        help="the smallest amount loss needs to improve by to be considered "
                             "improvement by early stopping.")
    parser.add_argument('--use-class-weights', type=bool, default=True,
                        help="whether to weight the value of class loss and accuracy based on "
                             "their support.")
    parser.add_argument('--validation-split', type=float, default=0.2,
                        help="the fraction of the data to use for validation.")
    parser.add_argument('--optimizer', default='nadam',
                        help="the keras optimizer to use. default is 'nadam'")
    parser.add_argument('--batch-size', default=32,
                        help="The batch size to use during training.")
    parser.add_argument('--sequence-length', default=32,
                        help='The sequence size to use during training.')
    parser.add_argument('--sequence-stepping', action='store_true', default=False,
                        help="Whether to step entire sequences, creating non-overlapping "
                             "sequences, instead of the default, which is to step one token at a "
                             "time and create overlapping sequences.")
    parser.add_argument('--job-dir', type=Path, required=True,
                        help="Path to the output directory where logs and models will be "
                             "written.")
    parser.add_argument('--input-directory', type=Path, help="input directory")
    parser.add_argument('--log-name', help='A name for the tensorboard log file / checkpoints.')
    return parser


def train_on_data(model, config, train_data, validation_data, job_dir):
    log_name = build_log_name()

    callbacks = []

    if config.tensorboard:
        log_path = PurePath(job_dir) / "logs" / log_name
        tensorboard = TensorBoard(log_dir=log_path)
        callbacks.append(tensorboard)

    if config.checkpoints:
        checkpoint = ModelCheckpoint(PurePath(job_dir) / "models" / (log_name + ".h5"),
                                     verbose=1,
                                     save_best_only=True)
        callbacks.append(checkpoint)

    model.compile(optimizer=config.optimizer,
                  sample_weight_mode='temporal',
                  loss='binary_crossentropy',
                  weighted_metrics=['binary_accuracy'])

    if config.early_stopping:
        stopping = EarlyStopping(patience=config.early_stopping_patience,
                                 min_delta=config.early_stopping_delta)
        callbacks.append(stopping)

    model.fit(train_data,
              validation_data=validation_data,
              epochs=config.epochs,
              callbacks=callbacks)


def train_model(model, config):
    train, validation = train_validation(config.input_directory / 'train.tfrecord',
                                         config.input_directory / 'validation.tfrecord',
                                         batch_size=config.batch_size)
    train_on_data(model, config, train, validation, config.job_dir)


def build_log_name(log_name=None):
    return (log_name if log_name is not None else "") + "{}".format(time())
