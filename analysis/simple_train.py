#!/usr/bin/env python3
"""
Simplified training script that bypasses complex feature extraction
"""

import sys
import os
import pickle
import numpy as np
from scipy.stats import multivariate_normal as mvn
import pandas as pd

# Add the current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from bif_lakshay import process_flows

def extract_simple_features(flows):
    """Extract simple statistical features from BiF traces"""
    features = []
    
    for port, flow_data in flows.items():
        if len(flow_data['windows']) < 50:  # Skip very short flows
            continue
            
        windows = np.array(flow_data['windows'])
        times = np.array(flow_data['times'])
        
        # Skip if no variation
        if np.std(windows) < 100:
            continue
            
        # Extract simple statistical features
        feature_vector = [
            np.mean(windows),           # Mean BiF
            np.std(windows),            # BiF variation  
            np.max(windows),            # Peak BiF
            np.min(windows),            # Min BiF
            np.percentile(windows, 75), # 75th percentile
            np.percentile(windows, 25), # 25th percentile
            len(windows),               # Flow length (packets)
            times[-1] - times[0],       # Flow duration
        ]
        
        features.append(feature_vector)
    
    return features

def train_simple_classifier(ccs, train_files):
    """Train a simple classifier using statistical features"""
    
    print("=== SIMPLIFIED NEBBY TRAINING ===")
    
    # Collect features for each CCA
    cca_features = {}
    
    for cca in ccs:
        print(f"\nProcessing {cca}...")
        cca_files = [f for f in train_files if f.startswith(cca + "-")]
        
        if not cca_files:
            print(f"  No files found for {cca}")
            continue
            
        all_features = []
        
        for file in cca_files:
            try:
                flows = process_flows(file, "../measurements/", p="n")
                features = extract_simple_features(flows)
                
                if features:
                    all_features.extend(features)
                    print(f"  {file}: {len(features)} features extracted")
                else:
                    print(f"  {file}: No valid features")
                    
            except Exception as e:
                print(f"  {file}: Error - {e}")
        
        if len(all_features) >= 2:  # Need at least 2 samples
            cca_features[cca] = np.array(all_features)
            print(f"  Total features for {cca}: {len(all_features)}")
        else:
            print(f"  Not enough features for {cca}")
    
    # Train Gaussian models for each CCA
    models = {}
    for cca, features in cca_features.items():
        try:
            mean = np.mean(features, axis=0)
            cov = np.cov(features, rowvar=False)
            
            # Add regularization for numerical stability
            cov += np.eye(len(mean)) * 1e-6
            
            models[cca] = {'mean': mean, 'cov': cov}
            print(f"Trained model for {cca}")
            
        except Exception as e:
            print(f"Failed to train model for {cca}: {e}")
    
    return models

def test_simple_classifier(models, ccs, test_files):
    """Test the simple classifier"""
    
    print("\n=== TESTING CLASSIFIER ===")
    
    results = {}
    
    for cca in ccs:
        cca_files = [f for f in test_files if f.startswith(cca + "-")]
        correct = 0
        total = 0
        
        for file in cca_files:
            try:
                flows = process_flows(file, "../measurements/", p="n")
                features = extract_simple_features(flows)
                
                for feature_vector in features:
                    total += 1
                    
                    # Calculate probability for each model
                    probs = {}
                    for model_cca, model in models.items():
                        try:
                            prob = mvn.pdf(feature_vector, 
                                         mean=model['mean'], 
                                         cov=model['cov'], 
                                         allow_singular=True)
                            probs[model_cca] = prob
                        except:
                            probs[model_cca] = 0
                    
                    # Predict the CCA with highest probability
                    if probs:
                        predicted = max(probs.items(), key=lambda x: x[1])[0]
                        if predicted == cca:
                            correct += 1
                        
            except Exception as e:
                print(f"Error testing {file}: {e}")
        
        if total > 0:
            accuracy = (correct / total) * 100
            results[cca] = accuracy
            print(f"{cca}: {correct}/{total} = {accuracy:.1f}%")
        else:
            results[cca] = 0
            print(f"{cca}: No test data")
    
    return results

def main():
    # Full CCA list from original Nebby
    ccs = ['bic','highspeed','htcp','lp','nv','scalable','vegas','veno','westwood','yeah','cubic','reno']
    
    # Find training files
    measurements_dir = "../measurements"
    train_files = []
    
    for filename in os.listdir(measurements_dir):
        if filename.endswith("-tcp.csv"):
            base_name = filename.replace("-tcp.csv", "")
            train_files.append(base_name)
    
    print(f"Found {len(train_files)} training files")
    
    if len(train_files) == 0:
        print("No training files found!")
        return
    
    # Train the classifier
    models = train_simple_classifier(ccs, train_files)
    
    if not models:
        print("No models could be trained!")
        return
    
    # Test the classifier
    results = test_simple_classifier(models, ccs, train_files)
    
    # Save the model
    model_file = "../simple_nebby_model.pkl"
    with open(model_file, "wb") as f:
        pickle.dump(models, f)
    
    print(f"\n=== RESULTS ===")
    print(f"Model saved to: {model_file}")
    print(f"Trained CCAs: {list(models.keys())}")
    
    avg_accuracy = np.mean([acc for acc in results.values() if acc > 0])
    print(f"Average accuracy: {avg_accuracy:.1f}%")

if __name__ == "__main__":
    main()