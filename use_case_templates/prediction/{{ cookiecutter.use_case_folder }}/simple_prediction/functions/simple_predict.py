import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

import lazypredict
from lazypredict.Supervised import LazyRegressor, LazyClassifier
from sklearn.datasets import load_diabetes, load_breast_cancer

import autokeras as ak

from sklearn.metrics import accuracy_score, balanced_accuracy_score, roc_auc_score, f1_score, r2_score, mean_squared_error

from joblib import dump

def get_example_data(default):
    if default == "default regression":
        data = load_diabetes(as_frame=True)
        X = data['data']
        y = data['target']
        X['target'] = y
    elif default == "default classification":
        data = load_breast_cancer(as_frame=True)
        X = data['data']
        y = data['target']
        X['target'] = y
    X.to_csv("example_data.csv", index=False)
    return "example_data.csv"


class SimplePredict:
    def __init__(self, filepath, target, continuous_target):
        self.filepath = filepath
        self.target = target
        self.continuous = continuous_target

    # Read data from specified filepath
    def read_data(self):
        df = pd.read_csv(self.filepath)
        X = df.drop([self.target], axis=1)
        y = df[self.target]
        return X, y

    # Bar plot of model metrics
    def plot_top_metrics(self, top, metrics, metric="default"):
        if metric == "default":
            if self.continuous:
                metric="R-Squared"
            else:
                metric="Accuracy"
        plt.bar(metrics.index[:top], metrics[metric][:top])
        plt.title("Performance of Top " + str(top) +  " models")
        plt.xlabel("Model")
        plt.ylabel("r2 score")
        plt.xticks(rotation=90)
        plt.show()

    # Get the corresponding lazy predictor for regression or classification
    def get_lazy(self):
        if self.continuous:
            lazy = LazyRegressor(verbose=0,ignore_warnings=False, predictions=True)
        else:
            lazy = LazyClassifier(verbose=0,ignore_warnings=False, predictions=True)
        return lazy

    # Get the corresponding autokeras predictor for regression or classification
    def get_autokeras(self):
        if self.continuous:
            auto = ak.StructuredDataRegressor(overwrite=True, max_trials=3)
        else:
            auto = ak.StructuredDataClassifier(overwrite=True, max_trials=3)
        return auto

    # Get the metric scores for chosen model
    def model_scores(self, model, metrics):
        if model == "Best":
            return metrics.iloc[0]
        else:
            return metrics.loc[model]

    def autokeras_scores(self, model, X_test, y_test):
        if self.continuous:
            index = ["Adjusted R-Squared", "R-Squared", "RMSE"]

            n = X_test.shape[0]
            p = X_test.shape[1]
            y_pred = model.predict(X_test)
            r2 = r2_score(y_test, y_pred)
            adjusted_r2 = 1-(1-r2)*(n-1)/(n-p-1)
            rmse = mean_squared_error(y_test, y_pred) ** 0.5
            scores = [adjusted_r2, r2, rmse]
            return pd.Series(scores, index=index)
        else:
            index = ["Accuracy", "Balanced Accuracy", "F1 Score"]
            scores = []

            y_pred = model.predict(X_test)
            scores.append(accuracy_score(y_test, y_pred))
            scores.append(balanced_accuracy_score(y_test, y_pred))
            scores.append(f1_score(y_test, y_pred))
            return pd.Series(scores, index=index)



    # Plot true vs prediction values and return predicted values
    def model_prediction(self, model, best_model, predictions, y_test):
        if model == "Best":
            return predictions[best_model]
        else:
            return predictions[model]
        plt.scatter(y_test, model_predict)
        plt.title("True value vs Predicted value")
        plt.xlabel("True Value")
        plt.ylabel("Predicted Value")
        plt.show()

    # Get pipeline for specified model, can call predict() to get prediction from raw X data
    def get_model_pipeline(self, model, metrics, models):
        if model == "Best":
            best_model = metrics.index[0]
            return models[best_model]
        else:
            return models[model]

    # Save model pipeline as joblib artefact
    def save_pipeline(self, pipeline, filepath):
        dump(pipeline, filepath) 