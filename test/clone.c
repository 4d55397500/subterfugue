
#include <sched.h>
#include <stdio.h>
#include <stdlib.h>

int kidfunc(void *arg) {
  fprintf(stderr, "child\n");
  sleep(12);
  fprintf(stderr, "child done\n");
}


int main() {
  void *kidstack = malloc(2 * 1024 * 1024);

  int kid;
  if (kid = __clone(kidfunc, kidstack, 0, 0)) {
    fprintf(stderr, "parent (child is %d)\n", kid);
    sleep(5);
  }

  fprintf(stderr, "parent done\n");
}
