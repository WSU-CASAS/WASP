// hmm.c
//
// Written by Diane Cook, Washington State University, 2010
//
// Hidden Markov model code.

#include "ar.h"
#include "hmm.h"
#include <unistd.h>
#include <sys/times.h>

// Use a hidden Markov model to learn model of activities.
void HMMTrain(int cvnum) {
	int i, j, k, n, num = 0, snum, id, start, previous, label;

	if (mode == TRAIN)
		printf("HMM Train\n");
	else
		printf("HMM Train (CV fold %d of %d) ...\n\n", cvnum + 1, K);
	if (stream == 0) // Process as whole segmented data
			{
		for (i = 0; i < numactivities; i++) // Look at each activity
				{
			for (j = 0; j < afreq[i]; j++) // Look at each activity occurrence
					{
				// Train on K-1/K data
				if ((mode == TRAIN) || (K == 1) || (partition[num] != cvnum)) {
					start = starts[i][j];
					snum = lengthactivities[i][j];
					for (k = 0, n = 0; n < snum; k++) {
						// Ignore motion sensor off events and temperature events
						id = aevents[start + k][SENSOR];
						// Track features for this sensor event
						// Only consider events that are part of this activity,
						// ignore events for overlapping activities
						if (i == aevents[start + k][LABEL]) {
							CalculateState(aevents[start + k], sizes[i][j],
									previousactivity[i][j]);
							sfreq[i][id] += 1;
							// Update frequency for these sensor event values
							// for this activity
							CalculateEvidence(evidence[i]);
							stotal[i] += 1;
							n++;
						}
					}
					// Update transition frequency from previous activity
					// to this activity
					tr[previousactivity[i][j]][i] += (double) 1.0;
				}
				num++;
			}
		}
	} else // Process as a continuous data stream
	{
		previous = 0;
		start = 0;
		for (i = 0; i < evnum; i++) {
			label = aevents[i][LABEL];
			id = aevents[i][SENSOR];
			CalculateState(aevents[i], i - start, previous);
			sfreq[label][id] += 1;
			stotal[label] += 1;
			CalculateEvidence(evidence[label]);
			if (i > 0)
				tr[previous][label] += (double) 1.0;
			else
				tr[label][label] += (double) 1.0;
			if (label != previous) {
				previous = label;
				start = i;
			}
		}
	}
}

// Calculate the emission probabilities from the observed evidence, or the
// probability of observing the feature values given a particular activity.
void CalculateEmission() {
	int i, j, k;
	double val, min = 0.0000001;

	for (i = 0; i < numactivities; i++)
		for (j = 0; j < numfeatures; j++)
			for (k = 0; k < numfeaturevalues[j]; k++) {
				if (evidence[i][j][k] == 0) // Replace 0 values with small number
					val = min;
				else
					val = (double) evidence[i][j][k];

				// Probability of sensor event given activity i
				if (stotal[i] == 0)
					emissionProb[i][j][k] = min;
				else
					emissionProb[i][j][k] = val / (double) stotal[i];
			}
}

// Normalize the transition probabilities so they sum to one.
void NormalizeTransitionProb() {
	int i, j;
	double total;

	for (i = 0; i < numactivities; i++) {
		total = (double) 0;
		for (j = 0; j < numactivities; j++)
			total += tr[i][j];

		for (j = 0; j < numactivities; j++) {
			if (total != (double) 0)
				tr[i][j] /= total;
		}
	}
}

// Use Viterbi algorithm to update likelihood of each activity given
// most recent observed event
void UpdateLikelihood(int *event) {
	int i, j;
	LargeNumber emission;
	LargeNumber total = MakeLargeNumber((long double) 0);
	LargeNumber zero = MakeLargeNumber((long double) 0);

	for (i = 0; i < numactivities; i++) // Update likelihoods for each activity
			{
		emission = MakeLargeNumber((long double) 1);

		// Calculate the emission probability for activity i by
		// combining the probabilities of each feature value   
		for (j = 0; j < numfeatures; j++)
			emission = Multiply(emission, lemissionProb[i][j][svalues[j]]);

		// For each possible prior activity j, combine probability of
		// previous activity j with transition probability from j to i
		// and emission probability to get updated probability.
		// Note that likelihood was initialized earlier to the prior
		// probability for the activity.
		for (j = 0; j < numactivities; j++)
			likelihood[i] = Add(likelihood[i],
					Multiply(lprior[j], Multiply(ltr[j][i], emission)));
	}

	// Compute total of prior likelihoods
	for (i = 0; i < numactivities; i++)
		total = Add(total, likelihood[i]);
	// Normalize to make total equal 1
	for (i = 0; i < numactivities; i++) {
		if (!IsEqual(total, zero))
			lprior[i] = Divide(likelihood[i], total);
	}
}

// Generate activity label for sensor event sequence using HMM classifier.
void HMMTest(int cvnum) {
	int i, j, k, n, num=0, snum, id, label=-1, class, prev, start, previous;

	//if (mode == TEST)
	//	printf("HMM Test\n");
	//else
	//	printf("HMM Test (CV fold %d of %d) ...\n\n", cvnum + 1, K);
	CalculatePrior(); // Calculate prior probability for each activity

	// Calculate feature value probabilities for each activity (hidden state)
	CalculateEmission();
	NormalizeTransitionProb();
	MakeAllLarge(); // Represent probabilities in mantissa exponent format

	if (stream == 0) // Process as whole segmented data
			{
		for (i = 0; i < numactivities; i++) // Look at each activity
				{
			for (j = 0; j < afreq[i]; j++) // Look at each activity occurrence
					{
				// Test on 1/K data
				if ((mode == TEST) || (K == 1) || (partition[num] == cvnum)) {
					start = starts[i][j];
					TestInit();
					snum = lengthactivities[i][j];
					prev = -1;
					for (k = 0, n = 0; n < snum; k++) {
						// Only consider events that are part of this activity,
						// ignore events for overlapping activities
						if (i == aevents[start + k][LABEL]) {
							id = aevents[start + k][SENSOR];
							CalculateState(aevents[start + k], sizes[i][j],
									previousactivity[i][j]);
							CalculateEvidence(testevidence);
							// Compute likelihood of hidden state given sensor event
							UpdateLikelihood(aevents[start + k]);prev
							= label;
							if ((k == (snum - 1)) && (outputlevel > 2)) {
								printf(" event ");
								PrintEvent(aevents[start + k]);
							}
							n++;
						}
					}
					label = GetMax(); // Output label with greatest probability
					// Keep track of label frequencies for confusion matrix
					if (outputlevel > 2)
						printf("  activity %d label %d\n", i, label);
					freq[i][label] += 1;
					if (label == i) // Calculate classification accuracy
						right++;
					else
						wrong++;
				}
				num++;
			}
		}
	} else // Process as a continuous data stream
	{
		previous = 0;
		start = 0;
		for (i = 0; i < evnum - WINDOW; i++) // Test event at end of window
				{
			TestInit();
			prev = 0;
			for (j = 0; j < WINDOW; j++) {
				label = aevents[i + j][LABEL];
				id = aevents[i + j][SENSOR];
				CalculateState(aevents[i + j], i + j - start, previous);
				CalculateEvidence(testevidence);
				UpdateLikelihood(aevents[i + j]);
				if (aevents[i+j][LABEL] != previous)
				{
					previous = aevents[i+j][LABEL];
					start = i+j;
				}
				prev = 1;
			}
			if ((i + j) < (evnum - 1)) {
				if (label != aevents[i + j][LABEL]) {
					class = GetMax();
					freq[label][class] += 1;
					
					printf("%s    %s\n", adatetime[i+j], activitynames[class]);
					if (class == label)
						right++;
					else
						wrong++;
				} else {
					printf("%s    %s\n", adatetime[i+j], activitynames[label]);
				}
			}
		}
	}
}

// Return activity with the maximum likelihood.
int GetMax() {
	int i, activity = 0;
	LargeNumber max = MakeLargeNumber((long double) 0);

	for (i = 0; i < numactivities; i++) {
		if (IsGreaterThan(likelihood[i], max)) {
			max = likelihood[i];
			activity = i;
		}
	}

	return (activity);
}

// Save HMM to a file.
void SaveHMM(FILE *fp) {
	int i, j;

	for (i = 0; i < numactivities; i++)
		for (j = 0; j < numactivities; j++)
			fprintf(fp, "%lf ", tr[i][j]);
	fprintf(fp, "\n");
}

// Read HMM from a file.
void ReadHMM(FILE *fp) {
	int i, j;

	for (i = 0; i < numactivities; i++)
		for (j = 0; j < numactivities; j++)
			fscanf(fp, "%lf ", &(tr[i][j]));
	fscanf(fp, "\n");
}
