/*
 * Software Enginnering: Operating System
 * 
 * <Breif Example of Processes Management and Pipes>
 *
 * Author: Jin Kuan Zhou <zhoujk93@hotmail.com>
 * Date: 2016-02-02
 *
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/types.h>

int main(void)
{
    int fd[2], sum = 0;
    int status, my_int, int_recv;
    pid_t childpid;
        
    pipe(fd);
    
    if ((childpid = fork()) == -1) {
        perror("fork");
        exit(0);
    }
    
    if (childpid == 0) {
        /* Child process */
        close(fd[0]);
        
        while (1){
            printf("Enter an integer: ");
            status = scanf("%d", &my_int);
            if (status == EOF) {
                perror("stdin error");
                exit(0);
            } else if (status == 0) {
                printf("Not a valid integer\n");
                fseek(stdin,0,SEEK_END); // clear input buffer
            } else {
                printf("Child process send: %d\n", my_int);
                write(fd[1], &my_int, sizeof(my_int));
            }

            if (my_int == -1) break;
        }
        
        exit(0);
    } else {
        /* Parent Process */
        close(fd[1]);
        while(read(fd[0],&int_recv,sizeof(int_recv))) {
            if (int_recv != -1) {
                sum += int_recv;
                printf("Parent received integer: %d\n", int_recv);
            } else {
                printf("Total sum: %d\n", sum);
                break;   
            }
        }
    }
    
    return 0;
    
}
