// SPDX-License-Identifier: AGPL-3.0-only
// Copyright 2025 tajoumaru
//
// This file is part of 'ids.moe'. It is a derivative work of
// code from the 'animeApi' project by 'nattadasu'. The original license notices
// are preserved in the `NOTICE` file in the root of this repository.

import { Env } from './types';
import { handleRequest } from './router';

export default {
  async fetch(request: Request, env: Env, ctx: ExecutionContext): Promise<Response> {
    return handleRequest({ request, env, ctx });
  },
} satisfies ExportedHandler<Env>;
