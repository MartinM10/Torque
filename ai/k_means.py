from itertools import cycle

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
import operator
from kneed import KneeLocator
# pylint: disable=relative-beyond-top-level
from .common import generate_cluster_labels, get_base64, COLOR_LIST, generate_pc_columns_names


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
            if percentage_participation >= 90:
                break

            value = per[1]
            pca_most_important_features[per[0]] = value
            percentage_participation += value

        more_important_features[j] = pca_most_important_features

    return more_important_features


def get_time_series(feature_number, index_time_feature, features, x, n_clusters_, labels, cluster_centers, types):
    plt.clf()
    plt.figure(figsize=(6, 6))
    for k, col in zip(range(n_clusters_), COLOR_LIST):
        my_members = labels == k
        cluster_center = cluster_centers[k]
        # Se esta usando el feature 0 y 1 para plotear la clasificación, podria plotear otros features
        # Para los datasets de una unica sesion, se pueden plotear series temporales, con la clasificacion ya hecha,
        # resulta visualmente "atractivo"
        plt.plot(x[my_members, index_time_feature], x[my_members, feature_number], col + ".", label=types[k])
        plt.plot(cluster_center[index_time_feature], cluster_center[feature_number], "X", markerfacecolor=col,
                 markeredgecolor="k", markersize=10)
    xlabel = features[index_time_feature].swapcase() + ' (seconds)'
    plt.xlabel(xlabel, fontsize=10)
    ylabel = features[feature_number]
    if features[feature_number] == 'TRIP':
        ylabel = 'DISTANCE (KM)'
    elif features[feature_number] == 'FUEL_USED':
        ylabel = features[feature_number] + ' (L)'
    elif features[feature_number] == 'CO2':
        ylabel = features[feature_number] + ' (G/KM)'
    elif features[feature_number] == 'COOLANT':
        ylabel = features[feature_number] + ' (ºC)'
    elif features[feature_number] == 'SPEED':
        ylabel = features[feature_number] + ' (KM/H)'
    elif features[feature_number] == 'REVS':
        ylabel = features[feature_number] + ' (RPM)'
    elif features[feature_number] == 'LPK':
        ylabel = 'lITERS pER kILOMETER (L/KM)'

    plt.ylabel(ylabel.swapcase(), fontsize=10)
    plt.title('Time serie by clustering', fontsize=12)
    # plt.title("Estimated number of clusters: %d" % n_clusters_, fontsize=16)
    plt.legend()
    plt.grid()
    # plt.show()
    time_serie_plot = get_base64(plt).decode('ascii')  # To export
    plt.close()
    return time_serie_plot


def start(csv_file, filename):
    wcss = []

    # ==============================================================================
    # Read CSV file
    # ==============================================================================

    df = pd.read_csv(csv_file)
    original_df = df.copy()

    # ==============================================================================
    # Get features from the first row
    # ==============================================================================

    features = df.columns.values

    # ==============================================================================
    # delete SESSION_ID column from dataset
    # ==============================================================================

    if 'SESSION_ID' in features:
        df.drop(columns='SESSION_ID', inplace=True)
        features = np.delete(features, 0)

    # ==============================================================================
    # Remove features labels
    # ==============================================================================

    x = df.loc[:, features].values

    # ==============================================================================
    # Generate cumulative explanined variance ratio plot
    # ==============================================================================
    apply_pca = False
    more_important_features = None

    if 'all' in filename and 'type' not in filename:
        apply_pca = True

    if apply_pca:

        # ==============================================================================
        # Standardizing data (mean = 0 , variance = 1)
        # ==============================================================================

        x = StandardScaler().fit_transform(x)

        pca = PCA().fit(x)

        # ==============================================================================
        # Obtain optimal number of components based on explained variance ratio > = 0.9
        # ==============================================================================

        components_number = np.argmax(pca.explained_variance_ratio_.cumsum() >= 0.9) + 1

        # ==============================================================================
        # Plot Cumulative explained variance ratio
        # ==============================================================================

        plt.rc('axes', labelsize=16)  # Only needed first time

        plt.figure(figsize=(6, 6))
        plt.plot(range(1, pca.n_components_ + 1), pca.explained_variance_ratio_.cumsum(), marker='o', linestyle='-')
        plt.xlabel('Components number', fontsize=10)
        plt.ylabel('Cumulative explained variance', fontsize=10)
        plt.title('Cumulative explained variance ratio', fontsize=12)
        plt.vlines(components_number,
                   plt.ylim()[0],
                   plt.ylim()[1],
                   linestyles='dashed',
                   colors='m',
                   label='Cumulative explained variance >= 0.9')
        plt.legend()
        cumulative_explained_variance_ratio_plot = get_base64(plt).decode('ascii')
        plt.close()

        # ==============================================================================
        # Create PCA with optimal number of components previously obtained
        # ==============================================================================

        pca = PCA(n_components=components_number)

        '''
        
        # ==============================================================================
        # Fit model with the number of components selected
        # ==============================================================================
    
        x_scaled_reduced = pca.fit_transform(x)
        '''

        # ==============================================================================
        # Get PCA scores (create clusters based on the components scores)
        # ==============================================================================

        pca_scores = pca.fit_transform(x)

        # ==============================================================================
        # Get the principal features for each principal component
        # ==============================================================================

        more_important_features = get_pca_more_important_features(df, features, pca, components_number)

        '''
        if df.shape[1] > 20:
            iterations = 11
        else:
            iterations = df.shape[1]
        '''

        iterations = 11

        for i in range(1, iterations):
            kmeans = KMeans(n_clusters=i, init='k-means++', random_state=42)
            if 'all' in filename:
                kmeans.fit(pca_scores)
            else:
                kmeans.fit(x)
            wcss.append(kmeans.inertia_)

        # ==============================================================================
        # Find Elbow
        # ==============================================================================
        kneedle = KneeLocator(range(1, iterations), wcss, S=1.0, curve='convex', direction='decreasing')
        clusters_number = kneedle.knee

        # ==============================================================================
        # Plot Elbow with WCSS
        # ==============================================================================

        plt.figure(figsize=(6, 6))
        plt.plot(range(1, iterations), wcss, marker='o', linestyle='-')
        plt.vlines(clusters_number, plt.ylim()[0], plt.ylim()[1], linestyles='dashed', colors='m', label='knee/elbow')
        plt.legend()
        plt.xlabel("Clusters number", fontsize=10)
        plt.ylabel("Sum of squared distances", fontsize=10)
        plt.title('Elbow Method', fontsize=12)
        wcss_plot = get_base64(plt)  # To export
        plt.close()

        # ==============================================================================
        # Run k-means with the number of cluster chosen
        # ==============================================================================

        kmeans_pca = KMeans(n_clusters=clusters_number, init='k-means++', random_state=42)

        # ==============================================================================
        # Fit data with the k-means pca model
        # ==============================================================================

        kmeans_pca.fit(pca_scores)

        # ==============================================================================
        # Create dataset with results from PCA and the cluster column
        # ==============================================================================

        df_kmeans_pca = pd.concat([df.reset_index(drop=True), pd.DataFrame(x)], axis=1)
        df_kmeans_pca.columns.values[-len(features):] = generate_pc_columns_names(len(features))
        df_kmeans_pca['Kmeans value'] = kmeans_pca.labels_

        # ==============================================================================
        # Add cluster column with a label associated to each kmeans value
        # ==============================================================================

        df_kmeans_pca['Cluster'] = df_kmeans_pca['Kmeans value'].map(generate_cluster_map(clusters_number))

        # ==============================================================================
        # Create columns labels for each component
        # ==============================================================================

        pc_colums_names = generate_pc_columns_names(components_number)

        # ==============================================================================
        # Plot data by PCA components. The X axis is the first component, Y is the second
        # ==============================================================================
        # IF 'ALL' NOT IN FILENAME: PINTO VARIAS SERIES TEMPORALESS, EN CASO CONTRARIO PINTO UNA SOLA GRAFICA

        # variables used for plot
        labels = kmeans_pca.labels_
        cluster_centers = kmeans_pca.cluster_centers_
        labels_unique = np.unique(labels)
        n_clusters_ = len(labels_unique)
        types = generate_cluster_labels(n_clusters_)
        plt.figure(figsize=(6, 6))
        for k, col in zip(range(n_clusters_), COLOR_LIST):
            my_members = labels == k
            cluster_center = cluster_centers[k]
            # Se esta usando el feature 0 y 1 para plotear la clasificación, podria plotear otros features
            # Para los datasets de una unica sesion, se pueden plotear series temporales, con la clasificacion ya hecha,
            # resulta visualmente "atractivo"
            plt.plot(pca_scores[my_members, 0], pca_scores[my_members, 1], col + ".", label=types[k])
            plt.plot(cluster_center[0], cluster_center[1], "X", markerfacecolor=col, markeredgecolor="k", markersize=10)
        plt.xlabel('Component 1', fontsize=10)
        plt.ylabel('Component 2', fontsize=10)
        plt.title('Clusters by PCA components', fontsize=12)
        # plt.title("Estimated number of clusters: %d" % n_clusters_, fontsize=16)
        plt.legend()
        plt.grid()
        two_first_components_plot = get_base64(plt).decode('ascii')  # To export
        plt.close()

        # ==============================================================================
        # Print the amount of data that holds the components
        # ==============================================================================

        explained_variance_ratio = pca.explained_variance_ratio_

        # explained_variance_ratio_sum = pca.explained_variance_ratio_.cumsum()
        # print('explained variance: ', explained_variance_ratio_sum)

        # ==============================================================================
        # Create a plot for the porcetage of participation of each feature in each component
        # ==============================================================================
        plt.figure(figsize=(6, 6))
        plt.matshow(pca.components_, cmap='Blues')
        plt.yticks(range(len(pc_colums_names)), pc_colums_names, fontsize=10)
        plt.colorbar()
        plt.xlabel('Features', fontsize=10)
        plt.ylabel('Principal components', fontsize=10)
        plt.title('Components and Features', fontsize=12)
        plt.xticks(range(len(features)), features, rotation=90, ha='right', fontsize=8)
        components_and_features_plot = get_base64(plt, 'tight')
        plt.close()

        # ==============================================================================
        # Set data for SVM
        # ==============================================================================

        df['cluster'] = kmeans_pca.labels_
        original_df['cluster'] = kmeans_pca.labels_

        svm_params = {'df': df, 'x_scaled_reduced': x, 'clusters_number': clusters_number}

        return (
            None,  # all_time_series
            two_first_components_plot,
            components_and_features_plot.decode('ascii'),
            wcss_plot.decode('ascii'),
            cumulative_explained_variance_ratio_plot,
            explained_variance_ratio,
            pd.Series(kmeans_pca.labels_).to_json(orient='values'),
            more_important_features,
            svm_params,
            df,
            original_df
        )

    else:

        '''
        if df.shape[1] > 20:
            iterations = 11
        else:
            iterations = df.shape[1]
        '''

        iterations = 11

        for i in range(1, iterations):
            kmeans = KMeans(n_clusters=i, init='k-means++', random_state=42)
            kmeans.fit(x)
            wcss.append(kmeans.inertia_)

        # ==============================================================================
        # Find Elbow
        # ==============================================================================

        if 'type' in filename:
            s = 0.1
        else:
            s = 1.0

        kneedle = KneeLocator(range(1, iterations), wcss, S=s, curve='convex', direction='decreasing')
        clusters_number = kneedle.knee

        # ==============================================================================
        # Plot Elbow with WCSS
        # ==============================================================================

        plt.figure(figsize=(6, 6))
        plt.plot(range(1, iterations), wcss, marker='o', linestyle='-')
        plt.vlines(clusters_number, plt.ylim()[0], plt.ylim()[1], linestyles='dashed', colors='m', label='knee/elbow')
        plt.legend()
        plt.xlabel("Clusters number", fontsize=12)
        plt.ylabel("Sum of squared distances", fontsize=12)
        plt.title('Elbow Method', fontsize=16)
        wcss_plot = get_base64(plt)  # To export
        plt.close()

        # ==============================================================================
        # Run k-means with the number of cluster chosen
        # ==============================================================================

        kmeans = KMeans(n_clusters=clusters_number, init='k-means++', random_state=42)

        # ==============================================================================
        # Fit data with the k-means pca model
        # ==============================================================================
        kmeans.fit(x)
        # ==============================================================================
        # Create dataset with results from PCA and the cluster column
        # ==============================================================================

        df_kmeans_pca = pd.concat([df.reset_index(drop=True), pd.DataFrame(x)], axis=1)
        df_kmeans_pca.columns.values[-len(features):] = generate_pc_columns_names(len(features))
        df_kmeans_pca['Kmeans value'] = kmeans.labels_

        # ==============================================================================
        # Add cluster column with a label associated to each kmeans value
        # ==============================================================================

        df_kmeans_pca['Cluster'] = df_kmeans_pca['Kmeans value'].map(generate_cluster_map(clusters_number))

        # ==============================================================================
        # Plot data by PCA components. The X axis is the first component, Y is the second
        # ==============================================================================
        # IF 'ALL' NOT IN FILENAME: PINTO VARIAS SERIES TEMPORALESS, EN CASO CONTRARIO PINTO UNA SOLA GRAFICA

        all_time_series = None
        two_first_components_plot = None

        # variables used for plot two_first_components_plot
        labels = kmeans.labels_
        cluster_centers = kmeans.cluster_centers_
        labels_unique = np.unique(labels)
        n_clusters_ = len(labels_unique)
        types = generate_cluster_labels(n_clusters_)

        plt.figure(figsize=(6, 6))

        if 'type' in filename:
            for k, col in zip(range(n_clusters_), COLOR_LIST):
                my_members = labels == k
                cluster_center = cluster_centers[k]
                # Se esta usando el feature 0 y 1 para plotear la clasificación, podria plotear otros features Para
                # los datasets de una unica sesion, se pueden plotear series temporales, con la clasificacion ya
                # hecha, resulta visualmente "atractivo"
                plt.plot(x[my_members, 0], x[my_members, 1], col + ".", label=types[k])
                plt.plot(cluster_center[0], cluster_center[1], "X", markerfacecolor=col, markeredgecolor="k",
                         markersize=10)
            plt.xlabel('Component 1', fontsize=10)
            plt.ylabel('Component 2', fontsize=10)
            plt.title('Clusters by PCA components', fontsize=12)
            # plt.title("Estimated number of clusters: %d" % n_clusters_, fontsize=16)
            plt.legend()
            plt.grid()
            two_first_components_plot = get_base64(plt).decode('ascii')  # To export
            plt.close()

        else:

            # variables used for plot time series
            all_time_series = {}
            list_features = list(features)
            index_time_feature = list(features).index('TRIPTIME')

            for i in range(len(features)):
                if not i == index_time_feature:
                    all_time_series[list_features[i]] = get_time_series(i, index_time_feature, features, x, n_clusters_,
                                                                        labels, cluster_centers, types)

        # ==============================================================================
        # Set data for SVM
        # ==============================================================================

        df['cluster'] = kmeans.labels_
        original_df['cluster'] = kmeans.labels_

        svm_params = {'df': df, 'x_scaled_reduced': x, 'clusters_number': clusters_number}

        return (
            all_time_series,
            two_first_components_plot,  # None if 'type' in filename
            None,  # components_and_features_plot
            wcss_plot.decode('ascii'),
            None,  # cumulative_explained_variance_ratio_plot
            None,  # explained_variance_ratio
            pd.Series(kmeans.labels_).to_json(orient='values'),
            more_important_features,
            svm_params,
            df,
            original_df
        )
