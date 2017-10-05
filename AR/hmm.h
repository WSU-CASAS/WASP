// hmm.h

#ifndef HMM_H
#define HMM_H

void HMMTrain(int cvnum);
void HMMTest(int cvnum);
void CalculateEmission();
void NormalizeTransitionProb();
void UpdateLikelihood(int *event);
void SaveHMM(FILE *fp);
void ReadHMM(FILE *fp);
int GetMax();

#endif // HMM_H
