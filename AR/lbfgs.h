// lbfgs.h

#ifndef LBFGS_H
#define LBFGS_H

int lbfgs (long int *n, long int *m, double *x, double *f, double *g,
           long int *diagco, double *diag, long int *iprint, double *eps,
           double *xtol, double *w, long int *iflag);

#endif // LBFGS_H
