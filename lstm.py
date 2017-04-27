import os
import time
import warnings
import numpy as np
import time
import matplotlib.pyplot as plt
from numpy import newaxis
from keras.layers.core import Dense, Activation, Dropout
from keras.layers.recurrent import LSTM
from keras.models import Sequential, load_model

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3' #Hide messy TensorFlow warnings
warnings.filterwarnings('ignore') #Hide messy Numpy warnings

def load_data(filename, seq_len, normalise_window):
    '''
    Loads and normalize data
    '''
    f = open(filename, 'rb').read()
    data = f.decode().split('\n')

    sequence_length = seq_len + 1
    result = []
    for index in range(len(data) - sequence_length):
        result.append(data[index: index + sequence_length])

    if normalise_window:
        result = normalise_windows(result)

    result = np.array(result)

    row = round(0.9 * result.shape[0])
    train = result[:int(row), :]
    np.random.shuffle(train)
    x_train = train[:, :-1]
    y_train = train[:, -1]
    x_test = result[int(row):, :-1]
    y_test = result[int(row):, -1]

    x_train = np.reshape(x_train, (x_train.shape[0], x_train.shape[1], 1))
    x_test = np.reshape(x_test, (x_test.shape[0], x_test.shape[1], 1))

    return [x_train, y_train, x_test, y_test]

def normalise_windows(window_data):
    normalised_data = []
    for window in window_data:
        normalised_window = [((float(p) / float(window[0])) - 1) for p in window]
        normalised_data.append(normalised_window)
    return normalised_data

def build_model(layers):
    model = Sequential()

    model.add(LSTM(
        input_dim=layers[0],
        output_dim=layers[1],
        return_sequences=True))
    model.add(Dropout(0.2))

    model.add(LSTM(
        layers[2],
        return_sequences=False))
    model.add(Dropout(0.2))

    model.add(Dense(
        output_dim=layers[3]))
    model.add(Activation('linear'))

    start = time.time()
    print('> Compiling LSTM model....')

    model.compile(loss='mse', optimizer='rmsprop', metrics=['mae', 'acc'])

    print('> Compilation Time : ', time.time() - start)
    #print(model.summary())
    return model

def predict_point_by_point(model, data):
    #Predict each timestep given the last sequence of true data, in effect only predicting 1 step ahead each time
    predicted = model.predict(data)
    predicted = np.reshape(predicted, (predicted.size,))
    return predicted

def predict_sequence_full(model, data, window_size):
    #Shift the window by 1 new prediction each time, re-run predictions on new window
    curr_frame = data[0]
    predicted = []
    for i in range(len(data)):
        predicted.append(model.predict(curr_frame[newaxis, :, :])[0, 0])
        curr_frame = curr_frame[1:]
        curr_frame = np.insert(curr_frame, [window_size-1], predicted[-1], axis=0)
    return predicted

def predict_sequences_multiple(model, data, window_size, prediction_len):
    #Predict sequence of 50 steps before shifting prediction run forward by 50 steps
    prediction_seqs = []
    for i in range(int(len(data)/prediction_len)):
        curr_frame = data[i*prediction_len]
        predicted = []
        for j in range(prediction_len):
            predicted.append(model.predict(curr_frame[newaxis,:,:])[0,0])
            curr_frame = curr_frame[1:]
            curr_frame = np.insert(curr_frame, [window_size-1], predicted[-1], axis=0)
        prediction_seqs.append(predicted)
    return prediction_seqs



def calculate_price_movement(ticker, seq_len):
    global_start_time = time.time()
    print('> Started Calculations...')
    # Parameters
    stockFile = './data/lstm/'+ticker+'.csv'
    epochs = 20
    batch_size=512
    accs = []

    print('> Loading data... ')
    X_train, y_train, X_test, y_test = load_data(stockFile, seq_len, True)

    model = load_model('./model/lstm.h5')

    print('> LSTM trained, Testing model on validation set... ')

    training_start_time = time.time()

    hist = model.fit(
        X_train,
        y_train,
        batch_size=batch_size,
        nb_epoch=epochs,
        validation_split=0.05,
        verbose=0)

    print('> Testing duration (s) : ', time.time() - training_start_time)

    print('> Calculating Losses....')
    for key, value in hist.history.items():
        if(key == 'acc'):
            accs = value

    averageAccuracy = np.average(accs)

    print('> Plotting full sequence prediction....')
    predicted = predict_sequence_full(model, X_test, seq_len)

    return predicted, averageAccuracy




