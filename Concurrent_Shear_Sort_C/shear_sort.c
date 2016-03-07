/*
 * Software Enginnering: Operating System
 * 
 * <Implementation of Shearsort Algorithm Using POSIX Pthreads>
 *
 * Author: Jin Kuan Zhou <zhoujk93@hotmail.com>
 * Date: 2016-03-01
 *
 */

#include <stdio.h>
#include <stdlib.h>
#include <pthread.h>
#include <semaphore.h>

/* Thread argument struct type for thread function */
typedef struct _thread_data_type {
    int tid;
    //int *mat;
} thread_data_t;

/* Define global constants */
#define N 4
#define SEM_D_INIT_VAL 0

/* Define shared variables for threads */
int matrix[N][N];   /* NxN integers */
int done_count;     /* Number of threads that finish current phase */
sem_t delay[N];     /* One delay semaphore per thread */
pthread_mutex_t m;  /* Gives mutual exclusive access to done_count */

void swap(int *x, int *y);
void shear_sort(void *arg);

int main()
{
    int i, j, num;
    pthread_t threads[N];
    thread_data_t data[N];
    
    /* Read integers from file to the NxN matrix */
    FILE *fd = fopen("input.txt", "r");
    for(i = 0; i < N; i++)
    {
        for(j = 0; j < N; j++)
        {
            if (fscanf(fd, "%d", &num) > 0){
                matrix[i][j] = num;
            } else {
                printf("Failed to read NxN integers from input.txt\n");
                return -1;
            }
        }    
    }
    
    printf("Before shear sort:\n");
    for(i = 0; i < N; i++)
    {
        for(j = 0; j < N; j++)
        {
            printf("%d ", matrix[i][j]);
        }
        printf("\n");
    }
    printf("\n");
    
    /* Initialize semaphores */
    for (i = 0; i < N; i++) sem_init(&delay[i], 0, SEM_D_INIT_VAL);
    
    
    /* Initialize mutex */
    pthread_mutex_init(&m, NULL);
    
    /* Initialize global shared variable */
    done_count = 0;
    
    /* Spawn threads */
    for(i = 0; i < N; i++)
    {
        data[i].tid = i;
        if ((num = pthread_create(&threads[i], NULL, (void *) &shear_sort, (void *) &data[i]))){
            fprintf(stderr, "Failed to create thread %d, error code:%d\n", i, num);
            exit(-1);
        } else { printf("Spawned thread %d\n", i); }
    }
    
    /* Wait until all threads finish */
    for(i = 0; i < N; i++)
    {
        if ((num = pthread_join(threads[i], NULL))){
            fprintf(stderr, "Failed to join thread %d, error code:%d\n", i, num);
            exit(-1);
        } else { printf("Joined thread %d\n", i); }
    }
    
    /* Cleanup */
    for (i = 0; i < N; i++) sem_destroy(&delay[i]);
    pthread_mutex_destroy(&m);
    
    
    /* Check matrix content */
    printf("\nAfter shear sort:\n");
    for(i = 0; i < N; i++)
    {
        for(j = 0; j < N; j++)
        {
            printf("%d ", matrix[i][j]);
        }
        printf("\n");
    }    
    
    exit(0);
}

void shear_sort(void *arg)
{
    int tid, phase, i, step, temp;
    
    tid = ((thread_data_t*) arg)->tid;
    phase = 1;
    
    while(phase <= N+1)
    {
        if (phase % 2 == 1) {
        
            /* Odd phase, sort row */ 
            if (tid % 2 == 0) {
                /* Even row, sort in ascending order (min -> max) */
                for (step = 0; step < N-1; step++)
                {
                    for (i = 0; i < N-step-1; i++)
                    {
                        if (matrix[tid][i] > matrix[tid][i+1])
                            swap(&matrix[tid][i], &matrix[tid][i+1]);
                    }
                }
            } else {
                /* Odd row, sort in descending order (max -> min) */
                for (step = 0; step < N-1; step++)
                {
                    for (i = 0; i < N-step-1; i++)
                    {
                        if (matrix[tid][i] < matrix[tid][i+1])
                            swap(&matrix[tid][i], &matrix[tid][i+1]);
                    }
                }
            }

        } else {
        
            /* Even phase, sort column */      
            for (step = 0; step < N-1; step++)
            {
                for (i = 0; i < N-step-1; i++)
                {
                    if (matrix[i][tid] > matrix[i+1][tid])
                        swap(&matrix[i][tid], &matrix[i+1][tid]);
                }
            }
        }
        
        /* complete current phase */
        phase++;
        
        /* lock mutex m */
        pthread_mutex_lock(&m);
        
        /* Critical Section Starts */
        done_count++;
        if (done_count == N){
            /*
             * This is the last thread that finish phase x,
             * unlock all other waiting threads and let them
             * move to next phase's computation
             */
            while (done_count > 0){
                done_count--;
                sem_post(&delay[done_count]);
            }
        }
        /* Citical Section Ends */
        
        pthread_mutex_unlock(&m);
        /* unlock mutex m */
        
        /* 
         * Note: Threads might be blocked here, because no 
         * thread can start next phase until each one of 
         * them finish the current phase.
         */
        printf("Thread %d: finished phase %d\n", tid, phase-1);
        sem_wait(&delay[tid]);
    }
    
    pthread_exit(0);
}

void swap(int *x, int *y)
{
    int temp = *x;
    *x = *y;
    *y = temp;
}





















