from bif_lakshay import *
from features_lakshay import *
from fit_lakshay import *
from train_lakshay import *
from globals_lakshay import MAX_DEG
import pandas as pd
import numpy as np

#TODO Add function for running on unknown files
#TODO Add feature on how to flag unreliable files

def collect_test_data(var, present_files):
    cc_coeff_test = getCCcoeff(var,present_files,ss=225,p="n",ft_thresh=1)
    vals_test, new_vals_test = getCoeff(cc_coeff_test)
    return vals_test, new_vals_test


from scipy.stats import multivariate_normal as mvn
def getPDensity(curr, cc_gaussian_params):
    prob = {}
    for cc in cc_gaussian_params:
        mn = cc_gaussian_params[cc]['mean']
        covar = cc_gaussian_params[cc]['covar']
        
        try:
            # Add numerical stability
            if np.any(np.isnan(curr)) or np.any(np.isinf(curr)):
                prob[cc] = 1e-10
                continue
                
            if np.any(np.isnan(mn)) or np.any(np.isinf(mn)):
                prob[cc] = 1e-10
                continue
                
            # Check if covariance matrix is valid
            if np.any(np.isnan(covar)) or np.any(np.isinf(covar)):
                prob[cc] = 1e-10
                continue
            
            # Ensure shapes match
            if len(curr) != len(mn):
                print(f"Shape mismatch for {cc}: curr={len(curr)}, mean={len(mn)}")
                prob[cc] = 1e-10
                continue
                
            curr_p = mvn.pdf(curr, mean=mn, cov=covar, allow_singular=True)
            
            # Handle numerical issues
            if np.isnan(curr_p) or np.isinf(curr_p) or curr_p <= 0:
                curr_p = 1e-10
                
            prob[cc] = curr_p
            
        except Exception as e:
            print(f"Error calculating probability for {cc}: {e}")
            prob[cc] = 1e-10
            
    return prob

def get_test_accuracy(vals_test, cc_gaussian_params):
    acc_m = {}
    successful_classifications = 0
    total_attempts = 0
    
    for cc in vals_test:
        if cc not in acc_m:
            acc_m[cc] = []
        if len(list(vals_test[cc].keys())) == 0:
            continue
            
        data = vals_test[cc][1]
        for curr in data:
            total_attempts += 1
            
            # Ensure curr is a proper numpy array
            try:
                curr = np.array(curr, dtype=float)
                if len(curr) == 0:
                    continue
            except:
                continue
                
            p_dense = getPDensity(curr, cc_gaussian_params)
            if p_dense:
                acc_m[cc].append(p_dense)
    
    top = {}
    error = {}
    
    for cc in acc_m:
        top[cc] = {}
        ind = 0
        
        for item in acc_m[cc]:
            try:
                ccs = np.array(list(item.keys()))
                vals = np.array(list(item.values()), dtype=float)
                
                # Handle edge cases
                if len(vals) == 0:
                    if cc not in error:
                        error[cc] = []
                    error[cc].append(ind)
                    ind += 1
                    continue
                
                # Remove any NaN or infinite values
                valid_mask = np.isfinite(vals) & (vals > 0)
                if not np.any(valid_mask):
                    if cc not in error:
                        error[cc] = []
                    error[cc].append(ind)
                    ind += 1
                    continue
                
                vals_clean = vals[valid_mask]
                ccs_clean = ccs[valid_mask]
                
                if len(vals_clean) == 0:
                    if cc not in error:
                        error[cc] = []
                    error[cc].append(ind)
                    ind += 1
                    continue
                
                # Check for all identical values
                if np.all(vals_clean == vals_clean[0]):
                    # If all probabilities are the same, choose randomly or use first
                    top[cc][ind] = {}
                    top[cc][ind]['cc'] = [ccs_clean[0]]
                    top[cc][ind]['vals'] = [vals_clean[0]]
                    top[cc][ind]['new_vals'] = [1.0]
                    successful_classifications += 1
                    ind += 1
                    continue
                
                # Normalize probabilities (use log probabilities for numerical stability)
                log_vals = np.log(vals_clean + 1e-15)  # Add small epsilon to avoid log(0)
                max_log_val = np.max(log_vals)
                normalized_log = log_vals - max_log_val
                normalized_probs = np.exp(normalized_log)
                
                # Ensure probabilities sum to something reasonable
                prob_sum = np.sum(normalized_probs)
                if prob_sum > 0:
                    normalized_probs = normalized_probs / prob_sum
                else:
                    normalized_probs = np.ones_like(normalized_probs) / len(normalized_probs)
                
                # Sort by probability
                sort_indices = np.argsort(normalized_probs)[::-1]  # Descending order
                
                cc_list = [ccs_clean[i] for i in sort_indices]
                vals_list = [vals_clean[i] for i in sort_indices]
                new_vals_list = [normalized_probs[i] for i in sort_indices]
                
                top[cc][ind] = {}
                top[cc][ind]['cc'] = cc_list[:3]  # Top 3
                top[cc][ind]['vals'] = vals_list[:3]
                top[cc][ind]['new_vals'] = new_vals_list[:3]
                
                successful_classifications += 1
                ind += 1
                
            except Exception as e:
                print(f"Error processing classification for {cc}, item {ind}: {e}")
                if cc not in error:
                    error[cc] = []
                error[cc].append(ind)
                ind += 1
                continue
    
    print(f"Classification success rate: {successful_classifications}/{total_attempts} = {successful_classifications/max(total_attempts,1)*100:.1f}%")
    return acc_m, top, error

def print_confusion_matrix(ccs, top):    
    matrix = []
    total_correct = 0
    total_classified = 0
    
    for cc in ccs:
        # The underlying CC
        temp = []
        total = len(top[cc].keys()) if cc in top else 0
        cc_index = ccs.index(cc)
        
        for check_cc in ccs:
            # The CC it gets classified as
            count = 0
            if cc in top:
                for i in range(0, len(top[cc].keys())):
                    if i not in top[cc]:
                        continue
                    if len(top[cc][i]['cc']) > 0 and top[cc][i]['cc'][0] == check_cc:
                        count += 1
            temp.append(count)
        
        if total > 0:
            correct = temp[cc_index]
            accuracy = (correct / total) * 100
            temp.append(f"{accuracy:.1f}%")
            total_correct += correct
            total_classified += total
        else:
            temp.append("NA")
        matrix.append(temp)
    
    rows = [cc for cc in ccs]
    columns = [cc for cc in ccs]
    columns.append("accuracy")
    
    df = pd.DataFrame(matrix, index=rows, columns=columns)
    print("Rows are the truth. Columns are the classifications")
    print(df)
    
    if total_classified > 0:
        overall_accuracy = (total_correct / total_classified) * 100
        print(f"\nOverall accuracy: {total_correct}/{total_classified} = {overall_accuracy:.1f}%")
    
    return df

def run_and_get_accuracy(train_cc_gaussian_params, ccs, present_files):
    print("Starting classification test...")
    vals, new_vals = collect_test_data(ccs, present_files)
    
    print(f"Test data collected for {len(vals)} CCAs")
    for cc, data in vals.items():
        if 1 in data:
            print(f"  {cc}: {len(data[1])} test samples")
    
    acc_m, top, error = get_test_accuracy(vals, train_cc_gaussian_params)
    
    print("\nClassification errors:")
    for cc, errors in error.items():
        if errors:
            print(f"  {cc}: {len(errors)} failed classifications")
    
    df = print_confusion_matrix(ccs, top)