import os
import glob
import gc
import logging
import numpy as np
import pandas as pd
from typing import Tuple, List, Dict
from sklearn.model_selection import StratifiedShuffleSplit
from sklearn.preprocessing import RobustScaler, LabelEncoder
from sklearn.feature_selection import VarianceThreshold
from sklearn.ensemble import RandomForestClassifier
import joblib

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler()]
)

class CICIDS2017Preprocessor:
    def __init__(self, raw_data_dir: str, processed_dir: str, features_dir: str):
        """
        Initializes the preprocessor pipeline.
        
        Args:
            raw_data_dir (str): Path to raw CSV files.
            processed_dir (str): Path to save cleaned and split datasets.
            features_dir (str): Path to save models (scalers, feature lists).
        """
        self.raw_data_dir = raw_data_dir
        self.processed_dir = processed_dir
        self.features_dir = features_dir
        
        # Ensure output directories exist
        os.makedirs(self.processed_dir, exist_ok=True)
        os.makedirs(self.features_dir, exist_ok=True)
        
        self.scaler = RobustScaler()
        self.label_encoder = LabelEncoder()
        
    def _reduce_memory_usage(self, df: pd.DataFrame) -> pd.DataFrame:
        """Iterates through all columns and converts data types to reduce memory footprint."""
        start_mem = df.memory_usage().sum() / 1024**2
        logging.info(f"Memory usage of dataframe is {start_mem:.2f} MB")
        
        for col in df.columns:
            col_type = df[col].dtype
            
            if col_type != object:
                c_min = df[col].min()
                c_max = df[col].max()
                if str(col_type)[:3] == 'int':
                    if c_min > np.iinfo(np.int8).min and c_max < np.iinfo(np.int8).max:
                        df[col] = df[col].astype(np.int8)
                    elif c_min > np.iinfo(np.int16).min and c_max < np.iinfo(np.int16).max:
                        df[col] = df[col].astype(np.int16)
                    elif c_min > np.iinfo(np.int32).min and c_max < np.iinfo(np.int32).max:
                        df[col] = df[col].astype(np.int32)
                    elif c_min > np.iinfo(np.int64).min and c_max < np.iinfo(np.int64).max:
                        df[col] = df[col].astype(np.int64)  
                else:
                    if c_min > np.finfo(np.float16).min and c_max < np.finfo(np.float16).max:
                        df[col] = df[col].astype(np.float32) # Using float32 instead of 16 for stability
                    elif c_min > np.finfo(np.float32).min and c_max < np.finfo(np.float32).max:
                        df[col] = df[col].astype(np.float32)
                    else:
                        df[col] = df[col].astype(np.float64)
                        
        end_mem = df.memory_usage().sum() / 1024**2
        logging.info(f"Memory usage after optimization: {end_mem:.2f} MB (Decreased by {100 * (start_mem - end_mem) / start_mem:.1f}%)")
        return df

    def load_and_merge(self) -> pd.DataFrame:
        """Loads all CSV files from the raw directory, cleans headers, and merges them."""
        csv_files = glob.glob(os.path.join(self.raw_data_dir, "*.csv"))
        if not csv_files:
            raise FileNotFoundError(f"No CSV files found in {self.raw_data_dir}")
        
        logging.info(f"Found {len(csv_files)} files. Beginning aggregation...")
        
        df_list = []
        for file in csv_files:
            logging.info(f"Reading {os.path.basename(file)}...")
            # Using engine='c' for speed, stripping whitespace in headers
            temp_df = pd.read_csv(file, low_memory=False, engine='c')
            
            # Clean column names immediately to avoid mismatch during concat
            temp_df.columns = temp_df.columns.str.strip()
            df_list.append(temp_df)
            
        merged_df = pd.concat(df_list, axis=0, ignore_index=True)
        del df_list
        gc.collect()
        
        logging.info(f"Merged Dataset Shape: {merged_df.shape}")
        return merged_df

    def clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Handles infinite values, NaNs, and drops empty variables."""
        logging.info("Cleaning data: replacing Inf with NaN, dropping NaNs, and handling duplicates...")
        
        # Replace infinite values with NaN
        df.replace([np.inf, -np.inf], np.nan, inplace=True)
        
        # Drop rows with NaN values
        initial_rows = df.shape[0]
        df.dropna(inplace=True)
        logging.info(f"Dropped {initial_rows - df.shape[0]} rows containing NaN or Infinite values.")
        
        # Drop duplicates
        initial_rows = df.shape[0]
        df.drop_duplicates(inplace=True)
        logging.info(f"Dropped {initial_rows - df.shape[0]} duplicate rows.")
        
        # Consolidate target labels (cleaning up 'Web Attack \xbc' style bugs if any exist)
        if 'Label' in df.columns:
            df['Label'] = df['Label'].apply(lambda x: x.encode('utf-8', 'ignore').decode('utf-8'))
            
        return self._reduce_memory_usage(df)

    def process_labels(self, df: pd.DataFrame) -> pd.DataFrame:
        """Creates Binary and Multi-class targets."""
        logging.info("Processing target variable 'Label'...")
        
        if 'Label' not in df.columns:
            raise KeyError("The dataset does not contain a 'Label' column.")
        
        # Multi-class target
        df['Label_Multi'] = df['Label']
        
        # Binary target (BENIGN = 0, ATTACK = 1)
        df['Label_Binary'] = df['Label'].apply(lambda x: 0 if x.strip() == 'BENIGN' else 1)
        
        logging.info(f"Class distribution (Binary):\n{df['Label_Binary'].value_counts(normalize=True)*100}")
        
        # Drop the original String label for numeric constraints later
        df.drop(columns=['Label'], inplace=True)
        return df

    def feature_engineering(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, list]:
        """Removes constant features, identifies highly correlated features, scales data."""
        logging.info("Starting Feature Engineering...")
        
        X = df.drop(columns=['Label_Binary', 'Label_Multi'])
        y_binary = df['Label_Binary']
        y_multi = df['Label_Multi']
        
        # 1. Variance Threshold (Remove Zero Variance features)
        var_thres = VarianceThreshold(threshold=0.0)
        var_thres.fit(X)
        const_columns = [column for column in X.columns if column not in X.columns[var_thres.get_support()]]
        logging.info(f"Dropping {len(const_columns)} constant variables: {const_columns}")
        X.drop(columns=const_columns, inplace=True)
        
        # 2. Scaling
        # RobustScaler is excellent for handling extreme outliers common in network traffic
        logging.info("Scaling numerical features with RobustScaler...")
        numeric_cols = X.select_dtypes(include=[np.number]).columns
        X[numeric_cols] = self.scaler.fit_transform(X[numeric_cols])
        
        # Save scaler for online inference
        joblib.dump(self.scaler, os.path.join(self.features_dir, "robust_scaler.pkl"))
        
        return pd.concat([X, y_binary, y_multi], axis=1), list(X.columns)

    def feature_selection(self, df: pd.DataFrame, num_features: int = 20) -> list:
        """Selects top K features using Random Forest Importance."""
        logging.info(f"Selecting Top {num_features} features using Random Forest representation...")
        
        X = df.drop(columns=['Label_Binary', 'Label_Multi'])
        y = df['Label_Binary']
        
        # Using a subset if dataset is massive to compute importance efficiently
        sample_size = min(300_000, X.shape[0])
        X_sample = X.sample(n=sample_size, random_state=42)
        y_sample = y.loc[X_sample.index]
        
        rf = RandomForestClassifier(n_estimators=50, n_jobs=-1, random_state=42)
        rf.fit(X_sample, y_sample)
        
        importances = pd.Series(rf.feature_importances_, index=X.columns)
        top_features = importances.nlargest(num_features).index.tolist()
        
        logging.info(f"Top {num_features} Features identified: {top_features}")
        
        # Save feature list for the streaming pipeline downstream
        joblib.dump(top_features, os.path.join(self.features_dir, "top_features.pkl"))
        
        return top_features

    def split_and_save(self, df: pd.DataFrame, top_features: list):
        """Creates train/test split and serializes data to disk in Parquet format."""
        logging.info("Splitting dataset into Train and Test sets (Stratified 80/20)...")
        
        # Keep only top features + Labels
        columns_to_keep = top_features + ['Label_Binary', 'Label_Multi']
        df = df[columns_to_keep]
        
        splitter = StratifiedShuffleSplit(n_splits=1, test_size=0.20, random_state=42)
        train_idx, test_idx = next(splitter.split(df, df['Label_Binary']))
        
        train_df = df.iloc[train_idx]
        test_df = df.iloc[test_idx]
        
        logging.info(f"Train Shape: {train_df.shape} | Test Shape: {test_df.shape}")
        
        # Save to parquet (much more compact and faster I/O than CSV)
        train_path = os.path.join(self.processed_dir, "train_dataset.parquet")
        test_path = os.path.join(self.processed_dir, "test_dataset.parquet")
        
        logging.info("Saving processed datasets to Parquet files...")
        train_df.to_parquet(train_path, index=False, engine='pyarrow')
        test_df.to_parquet(test_path, index=False, engine='pyarrow')
        
        logging.info("Data Pipeline Processing Complete!")

def run_pipeline():
    RAW_DIR = r"c:\Users\manoj\OneDrive\Desktop\AIML\data\raw\CICIDS2017"
    PROCESSED_DIR = r"c:\Users\manoj\OneDrive\Desktop\AIML\data\processed"
    FEATURES_DIR = r"c:\Users\manoj\OneDrive\Desktop\AIML\data\features"
    
    preprocessor = CICIDS2017Preprocessor(
        raw_data_dir=RAW_DIR,
        processed_dir=PROCESSED_DIR,
        features_dir=FEATURES_DIR
    )
    
    # Execute Pipeline
    try:
        df = preprocessor.load_and_merge()
        df = preprocessor.clean_data(df)
        df = preprocessor.process_labels(df)
        df, all_features = preprocessor.feature_engineering(df)
        top_features = preprocessor.feature_selection(df, num_features=25)
        preprocessor.split_and_save(df, top_features)
    except Exception as e:
        logging.error(f"Pipeline failed: {str(e)}")

if __name__ == "__main__":
    run_pipeline()
