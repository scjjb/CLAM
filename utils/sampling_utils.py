import numpy as np
import math

def generate_sample_idxs(idxs_length,previous_samples,sampling_weights,samples_per_epoch,num_random,grid=False,coords=None):
    if grid:
        assert len(coords)>0
        x_coords=[x.item() for x,y in coords]
        y_coords=[y.item() for x,y in coords]
        min_x=min(x_coords)
        max_x=max(x_coords)
        min_y=min(y_coords)
        max_y=max(y_coords)
        
        num_of_splits=int(math.sqrt(samples_per_epoch))
        x_borders=np.linspace(min_x,max_x+0.00001,num_of_splits+1)
        y_borders=np.linspace(min_y,max_y+0.00001,num_of_splits+1)
        
        sample_idxs=[]
        coords_splits=[[] for _ in range((num_of_splits+1)*(num_of_splits+1))]
        for coord_idx, (x,y) in enumerate(coords):
            x_border_idx=np.where(x_borders==max(x_borders[x_borders<=x.item()]))[0][0]
            y_border_idx=np.where(y_borders==max(y_borders[y_borders<=y.item()]))[0][0]
            coords_splits[(num_of_splits+1)*x_border_idx+y_border_idx].append(coord_idx)
        for coords_in_split in coords_splits:
            if len(coords_in_split)>0:
                sample_idxs=sample_idxs+list(np.random.choice(coords_in_split, size=1,replace=False))
        if len(sample_idxs)<samples_per_epoch:
            sample_idxs=sample_idxs+list(np.random.choice(range(0,len(coords)), size=samples_per_epoch-len(sample_idxs),replace=False))

    else:
        available_idxs=set(range(idxs_length))
        nonrandom_idxs=[]
        random_idxs=[]
        if int(samples_per_epoch-num_random)>0:
            nonrandom_idxs=list(np.random.choice(range(idxs_length),p=sampling_weights,size=int(samples_per_epoch-num_random),replace=False))
            previous_samples=previous_samples+nonrandom_idxs
            available_idxs=available_idxs-set(previous_samples)
        if num_random>0:
            random_idxs=list(np.random.choice(list(available_idxs), size=num_random,replace=False))
        sample_idxs=random_idxs+nonrandom_idxs
    return sample_idxs


def generate_features_array(args, data, coords, slide_id, slide_id_list, texture_dataset):
    if args.sampling_type=='spatial':
        X = np.array(coords)
    elif args.sampling_type=='textural':
        assert args.texture_model in ['resnet50','levit_128s'], 'incorrect texture model chosen'
        if args.texture_model=='resnet50':
            X = np.array(data)
        else:
            texture_index=slide_id_list.index(slide_id[0][0])
            levit_features=texture_dataset[texture_index][0]
            assert len(levit_features)==len(data),"features length mismatch"
            X = np.array(levit_features)
    return X


def update_sampling_weights(sampling_weights, attention_scores, all_sample_idxs, indices, neighbors, power=0.15, normalise = True, sampling_update = 'max', repeats_allowed = False):
    """
    Updates the sampling weights of all patches by looping through the most recent sample and adjusting all neighbors weights
    By default the weight of a patch is the maximum of its previous weight and the newly assigned weight, though sampling_average changes this to an average
    power is a hyperparameter controlling how attention scores are smoothed as typically very close to 0 or 1
    if repeated_allowed = False then weights for previous samples are set to 0
    """
    assert sampling_update in ['max','average','none']
    if sampling_update=='average':
        for i in range(len(indices)):
            for index in indices[i][:neighbors]:
                if sampling_weights[index]>0:
                    sampling_weights[index]=(sampling_weights[index]+pow(attention_scores[i],power))/2
                else:
                    sampling_weights[index]=pow(attention_scores[i],power)
    elif sampling_update=='max':
        for i in range(len(indices)):
            #print("indices:",len(indices))
            for index in indices[i][:neighbors]:
                sampling_weights[index]=max(sampling_weights[index],pow(attention_scores[i],power))

    if not repeats_allowed:
        for sample_idx in all_sample_idxs:
            sampling_weights[sample_idx]=0

    if normalise:
        sampling_weights=sampling_weights/max(sampling_weights)
        sampling_weights=sampling_weights/sum(sampling_weights)

    return sampling_weights
