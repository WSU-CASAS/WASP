# Makefile
#
# AR
#
CC = gcc
CFLAGS = -Wall -g -c
LFLAGS = -lm

SRCS = ar.c nb.c hmm.c crf.c lbfgs.c
OBJS = $(SRCS:.c=.o)
TARGETS = ar

all:	$(TARGETS)

ar:	$(OBJS)
	$(CC) -o ar $(OBJS) $(LFLAGS)

ar.o:	ar.c ar.h
	$(CC) $(CFLAGS) ar.c -o ar.o

nb.o:	nb.c nb.h
	$(CC) $(CFLAGS) nb.c -o nb.o

hmm.o:	hmm.c hmm.h
	$(CC) $(CFLAGS) hmm.c -o hmm.o

crf.o:	crf.c crf.h
	$(CC) $(CFLAGS) crf.c -o crf.o

lbfgs.o:	lbfgs.c lbfgs.h
	$(CC) $(CFLAGS) lbfgs.c -o lbfgs.o

install:
	cp $(TARGETS) ../bin

clean:
	/bin/rm -f $(OBJS) $(TARGETS)
