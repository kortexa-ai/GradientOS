#pragma once

// Compile-time detection of IgH libecrt availability.
//
// When IgH is installed, `ecrt.h` should be available and RTCore will compile the
// real EtherCAT loop. Without it, RTCore builds in "IPC-only" mode.
//
// IMPORTANT:
// We gate on a build-system define (`GRADIENT_ECRT_ENABLED`) rather than using
// `__has_include(<ecrt.h>)` so that we also link the correct libraries when the
// header is present.

#ifndef GRADIENT_ECRT_ENABLED
#define GRADIENT_ECRT_ENABLED 0
#endif

#if GRADIENT_ECRT_ENABLED
#define GRADIENT_HAVE_ECRT 1
extern "C" {
#include <ecrt.h>
}
#else
#define GRADIENT_HAVE_ECRT 0
#endif

