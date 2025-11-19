#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
Vector Database 패키지
=============================================================================

Qdrant Vector Database 연동 모듈입니다.

Author: Youth Policy System Team
Version: 1.0.0
=============================================================================
"""

from .qdrant_client import QdrantVectorDB, VectorDBConfig

__all__ = ['QdrantVectorDB', 'VectorDBConfig']
