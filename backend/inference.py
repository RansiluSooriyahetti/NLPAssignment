import tensorflow as tf
import re
import pickle
import numpy as np

# Constants (match training config)
EMBEDDING_DIM = 256
UNITS = 1024

def preprocess_sentence(sentence):
    sentence = sentence.lower().strip()
    sentence = re.sub(r"([?.!\-\\,])", r" \1 ", sentence)
    sentence = re.sub(r"[^\u0D80-\u0DFFa-zA-Z?.!\-\\,']", " ", sentence)
    sentence = re.sub(r"\s+", " ", sentence)
    return f"<start> {sentence.strip()} <end>"

class Encoder(tf.keras.Model):
    def __init__(self, vocab_size, embedding_dim, enc_units, batch_sz):
        super(Encoder, self).__init__()
        self.batch_sz = batch_sz
        self.enc_units = enc_units
        self.embedding = tf.keras.layers.Embedding(vocab_size, embedding_dim)
        self.gru = tf.keras.layers.GRU(self.enc_units,
                                       return_sequences=True,
                                       return_state=True,
                                       recurrent_initializer='glorot_uniform')

    def call(self, x, hidden):
        x = self.embedding(x)
        output, state = self.gru(x, initial_state=hidden)
        return output, state

    def initialize_hidden_state(self):
        return tf.zeros((self.batch_sz, self.enc_units))

class BahdanauAttention(tf.keras.layers.Layer):
    def __init__(self, units):
        super(BahdanauAttention, self).__init__()
        self.W1 = tf.keras.layers.Dense(units)
        self.W2 = tf.keras.layers.Dense(units)
        self.V = tf.keras.layers.Dense(1)

    def call(self, query, values):
        query_with_time_axis = tf.expand_dims(query, 1)
        score = self.V(tf.nn.tanh(
            self.W1(values) + self.W2(query_with_time_axis)))
        attention_weights = tf.nn.softmax(score, axis=1)
        context_vector = attention_weights * values
        context_vector = tf.reduce_sum(context_vector, axis=1)
        return context_vector, attention_weights

class Decoder(tf.keras.Model):
    def __init__(self, vocab_size, embedding_dim, dec_units, batch_sz):
        super(Decoder, self).__init__()
        self.batch_sz = batch_sz
        self.dec_units = dec_units
        self.embedding = tf.keras.layers.Embedding(vocab_size, embedding_dim)
        self.gru = tf.keras.layers.GRU(self.dec_units,
                                       return_sequences=True,
                                       return_state=True,
                                       recurrent_initializer='glorot_uniform')
        self.fc = tf.keras.layers.Dense(vocab_size)
        self.attention = BahdanauAttention(self.dec_units)

    def call(self, x, hidden, enc_output):
        context_vector, attention_weights = self.attention(hidden, enc_output)
        x = self.embedding(x)
        x = tf.concat([tf.expand_dims(context_vector, 1), x], axis=-1)
        output, state = self.gru(x)
        output = tf.reshape(output, (-1, output.shape[2]))
        x = self.fc(output)
        return x, state, attention_weights

class Translator:
    def __init__(self, weight_dir):
        # Load tokenizers
        with open(f"{weight_dir}/inp_lang_tokenizer.pickle", 'rb') as f:
            self.inp_tokenizer = pickle.load(f)
        with open(f"{weight_dir}/targ_lang_tokenizer.pickle", 'rb') as f:
            self.targ_tokenizer = pickle.load(f)
        
        # Build vocab sizes
        self.vocab_inp_size = len(self.inp_tokenizer.word_index) + 1
        self.vocab_tar_size = len(self.targ_tokenizer.word_index) + 1
        
        # Initialize models (batch size=1 for inference)
        self.encoder = Encoder(self.vocab_inp_size, EMBEDDING_DIM, UNITS, 1)
        self.decoder = Decoder(self.vocab_tar_size, EMBEDDING_DIM, UNITS, 1)
        
        # Dummy forward pass to build models
        sample_enc = tf.ones((1, 10))
        hidden = self.encoder.initialize_hidden_state()
        enc_out, _ = self.encoder(sample_enc, hidden)
        dec_input = tf.expand_dims([self.targ_tokenizer.word_index['<start>']], 0)
        self.decoder(dec_input, hidden, enc_out)
        
        # Load weights
        self.encoder.load_weights(f"{weight_dir}/encoder.weights.h5")
        self.decoder.load_weights(f"{weight_dir}/decoder.weights.h5")
    
    def translate(self, sentence):
        # Preprocess input
        sentence = preprocess_sentence(sentence)
        
        # Tokenize and pad
        inputs = [self.inp_tokenizer.word_index.get(word, 0) 
                 for word in sentence.split(' ')]
        inputs = tf.keras.preprocessing.sequence.pad_sequences(
            [inputs], maxlen=50, padding='post'
        )
        inputs = tf.convert_to_tensor(inputs)
        
        # Initialize hidden state
        hidden = [tf.zeros((1, UNITS))]
        enc_out, enc_hidden = self.encoder(inputs, hidden)
        dec_hidden = enc_hidden
        dec_input = tf.expand_dims(
            [self.targ_tokenizer.word_index['<start>']], 0
        )
        
        result = []
        for _ in range(50):  # Max output length
            predictions, dec_hidden, _ = self.decoder(
                dec_input, dec_hidden, enc_out
            )
            predicted_id = tf.argmax(predictions[0]).numpy()
            
            # Stop if <end> token
            if self.targ_tokenizer.index_word[predicted_id] == '<end>':
                break
                
            result.append(self.targ_tokenizer.index_word[predicted_id])
            dec_input = tf.expand_dims([predicted_id], 0)
        
        return ' '.join(result)