import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
import random
import base64
import io
import json
import operator
from kneed import KneeLocator
# pylint: disable=relative-beyond-top-level
from .common import generate_cluster_labels, get_base64, COLOR_LIST, generate_pc_columns_names

# COLOR_LIST = ['b', 'g', 'r', 'c', 'm', 'y']


def generate_cluster_map(number):
    res = {}

    cluster_labels = generate_cluster_labels(number)

    for i in range(number):
        res[i] = cluster_labels[i]

    return res


def get_pca_more_important_features(df, features, pca, components_number):
    # Get identity matrix
    i = np.identity(df.shape[1])

    # Pass identity matrix to transform method to get weights (coeficients)
    coef = pca.transform(i)

    more_important_features = {}

    for j in range(components_number):
        pca_coef = {}
        cont = 0
        for pc in coef:
            pca_coef[features[cont]] = abs(pc[j])
            cont += 1

        # Calculate the percetange of each coeficient (percentage(i) = (lamba(i) * 100) / sum(lambas))
        percetage_sum = sum(pca_coef.values())
        pca_coef_percetage = {}
        for key in pca_coef:
            pca_coef_percetage[key] = (pca_coef[key] * 100) / percetage_sum

        # Order each feature coeficient percentage by it value
        pca_coef_percetage = sorted(pca_coef_percetage.items(),
                                    key=operator.itemgetter(1), reverse=True)

        # Get most important features to cover the 90% of participation
        percentage_participation = 0
        pca_most_important_features = {}

        for per in pca_coef_percetage:
            if (percentage_participation >= 90):
                break

            value = per[1]
            pca_most_important_features[per[0]] = value
            percentage_participation += value

        more_important_features[j] = pca_most_important_features

    return more_important_features


def start(csv_file):
    # Read CSV file
    df = pd.read_csv(csv_file)

    # Get features from the first row
    features = df.columns.values

    # Remove features labels
    x = df.loc[:, features].values

    # Standardizing data (mean = 0 , variance = 1)
    x = StandardScaler().fit_transform(x)
    # BORRAR INDICES, DE LA FUNCION EXPORTAR Y COMPROBAR EL NUMERO DE COMPONENTES

    # Generate cumulative explanined variance ratio plot
    plt.rc('axes', labelsize=16)  # Only needed first time
    pca = PCA().fit(x)
    plt.figure(figsize=(10, 10))
    plt.plot(np.cumsum(pca.explained_variance_ratio_))
    plt.xlabel('Components number', fontsize=14)
    plt.ylabel('Cumulative explained variance', fontsize=14)
    plt.title('Cumulative explained variance ratio', fontsize=16)
    # print('VARIANZA ACUMULADA: ', np.cumsum(pca.explained_variance_ratio_))
    components_number = np.argmax(np.cumsum(pca.explained_variance_ratio_) >= 0.9)
    plt.vlines(components_number, plt.ylim()[0], plt.ylim()[
        1], linestyles='dashed', colors='m', label='Cumulative explained variance >= 0.9')
    plt.legend()
    cumulative_explained_variance_ratio_plot = get_base64(plt)

    plt.clf()

    # print('la posicion del elemento es: ', components_number, 'su valor es: ',
     #     np.cumsum(pca.explained_variance_ratio_)[components_number])
    # Create pca
    pca = PCA(n_components=components_number)

    # Fit model with the number of components selected
    x_scaled_reduced = pca.fit_transform(x)

    # Get PCA scores (create clusters based on the components scores)
    pca_scores = pca.transform(x)
    # print('pca_scores: ', pca_scores)
    # Get the principal features for each principal component
    more_important_features = get_pca_more_important_features(
        df, features, pca, components_number)
    # print('more_important_features: ', more_important_features)
    # Fit kmeans using the data from PCA
    wcss = []
    for i in range(1, 21):
        kmeans_pca = KMeans(n_clusters=i, init='k-means++',
                            random_state=42)
        kmeans_pca.fit(pca_scores)
        wcss.append(kmeans_pca.inertia_)

    # Find elbow
    # print('wcs: ', wcss)
    kneedle = KneeLocator(range(1, 21), wcss, S=1.0,
                          curve='convex', direction='decreasing')

    # Plot wcss
    plt.figure(figsize=(10, 10))
    plt.plot(range(1, 21), wcss, marker='o', linestyle='--')
    plt.vlines(kneedle.knee, plt.ylim()[0], plt.ylim()[
        1], linestyles='dashed', colors='m', label='Elbow')
    plt.legend()
    plt.xlabel("Clusters number", fontsize=14)
    plt.ylabel("WCSS", fontsize=14)
    plt.title('WCSS', fontsize=16)
    wcss_plot = get_base64(plt)
    plt.clf()
    # print('knee: ', kneedle.knee)
    clusters_number = kneedle.knee

    # Run k-means with the number of cluster chosen
    kmeans_pca = KMeans(n_clusters=clusters_number,
                        init='k-means++', random_state=42)

    # Fit data with the k-means pca model
    kmeans_pca.fit(pca_scores)

    # Create dataset with results from PCA and the cluster column
    df_kmeans_pca = pd.concat(
        [df.reset_index(drop=True), pd.DataFrame(pca_scores)], axis=1)
    df_kmeans_pca.columns.values[-components_number:] = generate_pc_columns_names(
        components_number)
    df_kmeans_pca['Kmeans value'] = kmeans_pca.labels_

    # Add cluster column with a label associated to each kmeans value
    df_kmeans_pca['Cluster'] = df_kmeans_pca['Kmeans value'].map(
        generate_cluster_map(clusters_number))

    # Create columns labels for each component
    pc_colums_names = generate_pc_columns_names(components_number)

    # Plot two first compontens
    fig = plt.figure(figsize=(10, 10))
    ax = fig.add_subplot(1, 1, 1)
    ax.set_xlabel('Principal component 1', fontsize=14)
    ax.set_ylabel('Principal component 2', fontsize=14)
    ax.set_title('PCA', fontsize=16)
    targets = generate_cluster_labels(clusters_number)
    colors = COLOR_LIST
    for target, color in zip(targets, colors):
        indicesToKeep = df_kmeans_pca['Cluster'] == target
        ax.scatter(df_kmeans_pca.loc[indicesToKeep, 'pc1'],
                   df_kmeans_pca.loc[indicesToKeep, 'pc2'], c=color, s=50)
    ax.legend(targets)
    ax.grid()
    two_first_components_plot = get_base64(plt)

    # Print the amount of data that holds the components
    explained_variance_ratio = pca.explained_variance_ratio_

    # explained_variance_ratio_sum = pca.explained_variance_ratio_.cumsum()
    # print('explained variance: ', explained_variance_ratio_sum)

    # Create a plot for the porcetage of participation of each feature in each component
    plt.matshow(pca.components_, cmap='Blues')
    plt.yticks(range(len(pc_colums_names)), pc_colums_names, fontsize=12)
    plt.colorbar()
    plt.xlabel('Features', fontsize=14)
    plt.ylabel('Principal components', fontsize=14)
    plt.title('Components and Features', fontsize=16)
    plt.xticks(range(len(features)), features, rotation=90, ha='right')
    components_and_features_plot = get_base64(plt, 'tight')
    plt.clf()

    # Set data for SVM
    df['cluster'] = kmeans_pca.labels_
    svm_params = {'df': df, 'x_scaled_reduced': x_scaled_reduced,
                  'clusters_number': clusters_number}

    return (two_first_components_plot.decode('ascii'), components_and_features_plot.decode('ascii'),
            wcss_plot.decode('ascii'), cumulative_explained_variance_ratio_plot.decode(
        'ascii'), explained_variance_ratio,
            # pd.Series(explained_variance_ratio, dtype=float).to_json(orient='values'),
            pd.Series(kmeans_pca.labels_).to_json(orient='values'), more_important_features, svm_params)
