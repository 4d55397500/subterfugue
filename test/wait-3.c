

#include <stdio.h>
#include <wait.h>

int main(int argc, char *argv[]) {
  int pid, wpid;

  if (pid = fork()) {
    fprintf(stderr, "parent: I see kid with pid = %d\n", pid);
    sleep(3);
    while (!(wpid = wait4(pid, 0, 0, 0)))
      sleep(2);
    if (wpid == pid) {
      fprintf(stderr, "parent: waited on kid\n");
      exit(0);
    } else {
      perror("wait4 failed");
      exit(1);
    }
  } else {
    fprintf(stderr, "child: I'm here\n");
    sleep(1);
    fprintf(stderr, "child: exiting\n");
    exit(0);
  }
}
