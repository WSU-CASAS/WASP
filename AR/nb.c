// nb.c
//
// Written by Diane Cook, Washington State University, 2010
//
// Naive Bayes classifier code.

#include "ar.h"
#include "nb.h"

// Use a naive Bayes classifier to learn model of activities.
void NBCTrain(int cvnum) {
	int i, j, k, n, num = 0, snum, start, label, previous;

	//if (mode == TRAIN)
	//	printf("NB Train\n");
	//else
	//	printf("NB Train (CV fold %d of %d) ...\n", cvnum + 1, K);
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
						// Only consider events that are part of this activity,
						// ignore events for overlapping activities
						if (i == aevents[start + k][LABEL]) {
							CalculateState(aevents[start + k], sizes[i][j],
									previousactivity[i][j]);
							stotal[i] += 1;
							CalculateEvidence(evidence[i]);
							n++;
						}
					}
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
			CalculateState(aevents[i], i - start, previous);
			stotal[label] += 1;
			CalculateEvidence(evidence[label]);
			if (label != previous) {
				previous = label;
				start = i;
			}
		}
	}
}

// Generate activity label for sensor event sequence using naive Bayes
// classifier.
void NBCTest(int cvnum) {
	int i, j, k, n, snum, label, class, num=0, start, previous;
	double p[numactivities], minvalue, mprob;

	//if (mode == TEST)
	//	printf("NB Test\n");
	//printf("NB Test (CV fold %d of %d) ...\n", cvnum + 1, K);
	CalculatePrior(); // Determine prior probability for each activity

	if (stream == 0) // Process as whole segmented data
			{
		for (i = 0; i < numactivities; i++) // Look at each activity
				{
			for (j = 0; j < afreq[i]; j++) // Look at each activity occurrence
					{
				// Test on 1/K data
				if ((mode == TEST) || (K == 1) || (partition[num] == cvnum)) {
					start = starts[i][j];
					TestInit(); // Initialize test variables
					snum = lengthactivities[i][j];
					for (k = 0, n = 0; n < snum; k++) {
						// Only consider events that are part of this activity,
						// ignore events for overlapping activities
						if (i == aevents[start + k][LABEL]) {
							CalculateState(aevents[start + k], sizes[i][j],
									previousactivity[i][j]);
							// Calculate probability of feature values given activity
							CalculateEvidence(testevidence);
							n++;
						}
					}
					// Output activity yielding largest probability
					minvalue = 0;
					mprob = 0;
					for (k = 0; k < numactivities; k++) {
						p[k] = CalculateProb(prior[k], k);
						if ((k == 0) || (p[k] < mprob)) {
							minvalue = k;
							mprob = p[k];
						}
					}
					class = minvalue;

					// Keep track of label frequencies for confusion matrix
					freq[i][class] += 1;
					if (i == class)// Calculate classification accuracy
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
		for (i = 0; i < evnum - WINDOW; i++) // Process each sensor event in order
		{
			TestInit();
			label = aevents[i][LABEL];

			for (j = 0; j < WINDOW; j++) {
				CalculateState(aevents[i + j], i + j - start, previous);
				// Calculate probability of feature values given activity
				CalculateEvidence(testevidence);
				if (label != previous) {
					previous = label;
					start = i;
				}
			}
			minvalue = 0;
			mprob = 0;
			for (j = 0; j < numactivities; j++) {
				p[j] = CalculateProb(prior[j], j);
				if ((j == 0) || (p[j] < mprob)) {
					minvalue = j;
					mprob = p[j];
				}
			}
			class = minvalue;
			//printf("%s    %s\n", adatetime[i], activitynames[class]);

			freq[label][class] += 1;
			if (label == class)
				right++;
			else
				wrong++;
			if ((i%1000) == 0) {
				printf("%f\n", (float) right / (float) (right + wrong));
				right = 0;
				wrong = 0;
			}
		}
	}
}

// Calculate the probability that the sensor event sequence corresponds
// to the input activity a using the naive Bayes calculation.
// The Bayes formula is P(a|e) = P(e|a)P(a)/P(e), where a is the input
// activity and e is the evidence (features describing the sensor event.
// The prior probability, P(a), is input as parameter p.  The denominator,
// P(e), is the same for all activities and is therefore ignored.
// Because feature values appear multiple times for each data point,
// we calculate the product of each occurrence of the feature value
// in order to compute the probability of the event features given an
// activity a, or P(e|a).
double CalculateProb(double p, int a) {
	int i, j, trainval, testval;
	double ratio;

	p = (double) -1.0 * log(p); // Start with prior probability
	for (i = 0; i < numfeatures; i++) {
		for (j = 0; j < numfeaturevalues[i]; j++) {
			trainval = evidence[a][i][j];
			testval = testevidence[i][j];
			if (testevidence[i][j] != 0) // Only include evidence which exists
					{
				if (trainval == 0) // Replace 0 values with small number
					p -= log((double) testval) + log((double) MIN);
				else // P(e|a), multiplied over each event in the activity
				{
					ratio = (double) trainval / (double) stotal[a];
					p -= log((double) testval) + log(ratio);
				}
			}
		}
	}

	return (p);
}
