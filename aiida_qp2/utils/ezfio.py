#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#   EZFIO is an automatic generator of I/O libraries
#   Copyright (C) 2009 Anthony SCEMAMA, CNRS
#
#   This program is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation; either version 2 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License along
#   with this program; if not, write to the Free Software Foundation, Inc.,
#   51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#
#   Anthony Scemama
#   LCPQ - IRSAMC - CNRS
#   Universite Paul Sabatier
#   118, route de Narbonne
#   31062 Toulouse Cedex 4
#   scemama@irsamc.ups-tlse.fr

import os, sys
import time
import io as StringIO
from gzip import GzipFile
import tempfile
import threading
from functools import reduce


def version(x):
    b = [int(i) for i in x.split('.')]
    return b[2] + b[1] * 100 + b[0] * 10000


def size(x):
    return len(x)


def flatten(l):
    res = []
    for i in l:
        if hasattr(i, '__iter__') and not isinstance(i, str):
            res.extend(flatten(i))
        else:
            res.append(i)
    return res


def maxval(l):
    return reduce(max, l, l[0])


def minval(l):
    return reduce(min, l, l[0])


def reshape(l, shape):
    l = flatten(l)
    for d in shape[:-1]:
        buffer = []
        buffer2 = []
        i = 0
        while i < len(l):
            buffer2.append(l[i])
            if len(buffer2) == d:
                buffer.append(buffer2)
                buffer2 = []
            i += 1
        l = list(buffer)
    return l


def at(array, index):
    return array[index - 1]


def n_count_ch(array, isize, val):
    result = 0
    for i in array:
        if i == val:
            result += 1
    return result


n_count_in = n_count_ch
n_count_do = n_count_ch
n_count_lo = n_count_ch


def get_conv(type):
    if type in ['do', 're']:
        conv = float
    elif type in ['in', 'i8']:
        conv = int
    elif type == 'lo':

        def conv(a):
            if a == True:
                return 'T'
            elif a == False:
                return 'F'
            elif a.lower() == 't':
                return True
            elif a.lower() == 'f':
                return False
            else:
                raise TypeError
    elif type == 'ch':
        conv = lambda x: x.decode('utf-8').strip() if isinstance(
            x, bytes) else x.strip()
    else:
        raise TypeError
    return conv


class ezfio_obj(object):
    def __init__(self, read_only=False):
        self._filename = 'EZFIO_File'
        self.buffer_rank = -1
        self.read_only = read_only
        self.locks = {}

    def acquire_lock(self, var):
        locks = self.locks
        try:
            locks[var].acquire()
        except:
            locks[var] = threading.Lock()
            locks[var].acquire()

    def release_lock(self, var):
        self.locks[var].release()

    def set_read_only(self, v):
        self.read_only = v

    def get_read_only(self):
        return self.read_only

    def exists(self, path):
        if os.access(path + '/.version', os.F_OK) == 1:
            file = open(path + '/.version', 'r')
            v = file.readline().strip()
            file.close()
        else:
            return False

    def mkdir(self, path):
        if self.read_only:
            self.error('Read-only file.')
        if self.exists(path):
            self.error('mkdir', 'Group ' + path + ' exists')
        try:
            os.mkdir(path.strip())
        except OSError:
            pass
        file = open(path.strip() + '/.version', 'w')
        print(self.version, file=file)
        file.close()

    def error(self, where, txt):
        print('------------------------------------------------------------')
        print('EZFIO File     : ' + self.filename)
        print('EZFIO Error in : ' + where.strip())
        print('------------------------------------------------------------')
        print('')
        print(txt.strip())
        print('')
        print('------------------------------------------------------------')
        raise IOError

    def get_filename(self):
        if not self.exists(self._filename):
            self.mkdir(self._filename)
        return self._filename

    def set_filename(self, filename):
        self._filename = filename

    filename = property(fset=set_filename, fget=get_filename)

    def set_file(self, filename):
        self.filename = filename
        if not self.exists(filename):
            self.mkdir(filename)
            self.mkdir(filename + '/ezfio')
            os.system("""
LANG= date > %s/ezfio/creation
echo $USER > %s/ezfio/user
echo %s > %s/ezfio/library""" % (filename, filename, self.LIBRARY, filename))

    def open_write_buffer(self, dir, fil, rank):
        if self.read_only:
            self.error('Read-only file.')
        l_filename = dir.strip() + '/' + fil + '.gz'
        if self.buffer_rank != -1:
            self.error('open_write_buffer',
                       'Another buffered file is already open.')

        self.buffer_rank = rank
        assert (self.buffer_rank > 0)

        try:
            self.file = GzipFile(filename=l_filename, mode='wb7')
        except IOError:
            self.error('open_write_buffer', 'Unable to open buffered file.')

        self.file.write('%2d\n' % (rank, ))

    def open_read_buffer(self, dir, fil, rank):
        l_filename = dir.strip() + '/' + fil + '.gz'

        if self.buffer_rank != -1:
            self.error('open_read_buffer',
                       'Another buffered file is already open.')

        try:
            self.file = GzipFile(filename=l_filename, mode='rb')
        except IOError:
            self.error('open_read_buffer', 'Unable to open buffered file.')

        try:
            rank = eval(self.file.readline())
        except IOError:
            self.error('open_read_buffer', 'Unable to read buffered file.')

        self.buffer_rank = rank
        assert (self.buffer_rank > 0)
        return rank

    def close_buffer(self):
        assert (self.buffer_rank > 0)
        self.buffer_rank = -1
        self.file.close()

    def read_buffer(self, isize):

        if self.buffer_rank == -1:
            self.error('read_buffer', 'No buffered file is open.')

        indices = []
        values = []
        for i in range(isize):
            try:
                line = self.file.readline().split()
            except:
                return indices, values
            if len(line) == 0:
                return indices, values
            indices.append([int(i) for i in line[:-1]])
            values.append(eval(line[-1]))
        return indices, values

    def write_buffer(self, indices, values, isize):
        if self.read_only:
            self.error('Read-only file.')
        if self.buffer_rank == -1:
            self.error('write_buffer', 'No buffered file is open.')

        for i in range(isize):
            for j in indices[i]:
                self.file.write('%4d ' % (j, ))
            self.file.write('%24.15e\n' % (values[i], ))

    def get_version(self):
        return '2.0.7'

    version = property(fset=None, fget=get_version)

    def get_path_ezfio(self):
        result = self.filename.strip() + '/ezfio'
        self.acquire_lock('ezfio')
        try:
            if not self.exists(result):
                self.mkdir(result)
        finally:
            self.release_lock('ezfio')
        return result

    path_ezfio = property(fget=get_path_ezfio)

    def get_ezfio_creation(self):
        self.acquire_lock('ezfio_creation')
        try:
            result = self.read_ch(self.path_ezfio, 'creation')
        finally:
            self.release_lock('ezfio_creation')
        return result

    def set_ezfio_creation(self, creation):
        self.acquire_lock('ezfio_creation')
        try:
            self.write_ch(self.path_ezfio, 'creation', creation)
        finally:
            self.release_lock('ezfio_creation')

    ezfio_creation = property(fset=set_ezfio_creation, fget=get_ezfio_creation)

    def has_ezfio_creation(self):
        return (os.access(self.path_ezfio + '/creation', os.F_OK) == 1)

    def get_ezfio_user(self):
        self.acquire_lock('ezfio_user')
        try:
            result = self.read_ch(self.path_ezfio, 'user')
        finally:
            self.release_lock('ezfio_user')
        return result

    def set_ezfio_user(self, user):
        self.acquire_lock('ezfio_user')
        try:
            self.write_ch(self.path_ezfio, 'user', user)
        finally:
            self.release_lock('ezfio_user')

    ezfio_user = property(fset=set_ezfio_user, fget=get_ezfio_user)

    def has_ezfio_user(self):
        return (os.access(self.path_ezfio + '/user', os.F_OK) == 1)

    def get_ezfio_library(self):
        self.acquire_lock('ezfio_library')
        try:
            result = self.read_ch(self.path_ezfio, 'library')
        finally:
            self.release_lock('ezfio_library')
        return result

    def set_ezfio_library(self, library):
        self.acquire_lock('ezfio_library')
        try:
            self.write_ch(self.path_ezfio, 'library', library)
        finally:
            self.release_lock('ezfio_library')

    ezfio_library = property(fset=set_ezfio_library, fget=get_ezfio_library)

    def has_ezfio_library(self):
        return (os.access(self.path_ezfio + '/library', os.F_OK) == 1)

    def get_ezfio_last_library(self):
        self.acquire_lock('ezfio_last_library')
        try:
            result = self.read_ch(self.path_ezfio, 'last_library')
        finally:
            self.release_lock('ezfio_last_library')
        return result

    def set_ezfio_last_library(self, last_library):
        self.acquire_lock('ezfio_last_library')
        try:
            self.write_ch(self.path_ezfio, 'last_library', last_library)
        finally:
            self.release_lock('ezfio_last_library')

    ezfio_last_library = property(fset=set_ezfio_last_library,
                                  fget=get_ezfio_last_library)

    def has_ezfio_last_library(self):
        return (os.access(self.path_ezfio + '/last_library', os.F_OK) == 1)

    def get_path_ao_basis(self):
        result = self.filename.strip() + '/ao_basis'
        self.acquire_lock('ao_basis')
        try:
            if not self.exists(result):
                self.mkdir(result)
        finally:
            self.release_lock('ao_basis')
        return result

    path_ao_basis = property(fget=get_path_ao_basis)

    def get_ao_basis_ao_num(self):
        self.acquire_lock('ao_basis_ao_num')
        try:
            result = self.read_in(self.path_ao_basis, 'ao_num')
        finally:
            self.release_lock('ao_basis_ao_num')
        return result

    def set_ao_basis_ao_num(self, ao_num):
        self.acquire_lock('ao_basis_ao_num')
        try:
            self.write_in(self.path_ao_basis, 'ao_num', ao_num)
        finally:
            self.release_lock('ao_basis_ao_num')

    ao_basis_ao_num = property(fset=set_ao_basis_ao_num,
                               fget=get_ao_basis_ao_num)

    def has_ao_basis_ao_num(self):
        return (os.access(self.path_ao_basis + '/ao_num', os.F_OK) == 1)

    def get_ao_basis_ao_prim_num(self):
        rank = 1
        dims = list(range(rank))
        dims[0] = int(self.ao_basis_ao_num)

        dim_max = 1
        for d in dims:
            dim_max *= d
        self.acquire_lock('ao_basis_ao_prim_num')
        try:
            result = self.read_array_in(self.path_ao_basis, 'ao_prim_num',
                                        rank, dims, dim_max)
        finally:
            self.release_lock('ao_basis_ao_prim_num')
        return result

    def set_ao_basis_ao_prim_num(self, ao_prim_num):
        rank = 1
        dims = list(range(rank))
        dims[0] = int(self.ao_basis_ao_num)

        dim_max = 1
        for d in dims:
            dim_max *= d
        self.acquire_lock('ao_basis_ao_prim_num')
        try:
            self.write_array_in(self.path_ao_basis, 'ao_prim_num', rank, dims,
                                dim_max, ao_prim_num)
        finally:
            self.release_lock('ao_basis_ao_prim_num')

    ao_basis_ao_prim_num = property(fset=set_ao_basis_ao_prim_num,
                                    fget=get_ao_basis_ao_prim_num)

    def has_ao_basis_ao_prim_num(self):
        return (os.access(self.path_ao_basis + '/ao_prim_num.gz',
                          os.F_OK) == 1)

    def get_ao_basis_ao_nucl(self):
        rank = 1
        dims = list(range(rank))
        dims[0] = int(self.ao_basis_ao_num)

        dim_max = 1
        for d in dims:
            dim_max *= d
        self.acquire_lock('ao_basis_ao_nucl')
        try:
            result = self.read_array_in(self.path_ao_basis, 'ao_nucl', rank,
                                        dims, dim_max)
        finally:
            self.release_lock('ao_basis_ao_nucl')
        return result

    def set_ao_basis_ao_nucl(self, ao_nucl):
        rank = 1
        dims = list(range(rank))
        dims[0] = int(self.ao_basis_ao_num)

        dim_max = 1
        for d in dims:
            dim_max *= d
        self.acquire_lock('ao_basis_ao_nucl')
        try:
            self.write_array_in(self.path_ao_basis, 'ao_nucl', rank, dims,
                                dim_max, ao_nucl)
        finally:
            self.release_lock('ao_basis_ao_nucl')

    ao_basis_ao_nucl = property(fset=set_ao_basis_ao_nucl,
                                fget=get_ao_basis_ao_nucl)

    def has_ao_basis_ao_nucl(self):
        return (os.access(self.path_ao_basis + '/ao_nucl.gz', os.F_OK) == 1)

    def get_ao_basis_ao_power(self):
        rank = 2
        dims = list(range(rank))
        dims[0] = int(self.ao_basis_ao_num)
        dims[1] = int(3)

        dim_max = 1
        for d in dims:
            dim_max *= d
        self.acquire_lock('ao_basis_ao_power')
        try:
            result = self.read_array_in(self.path_ao_basis, 'ao_power', rank,
                                        dims, dim_max)
        finally:
            self.release_lock('ao_basis_ao_power')
        return result

    def set_ao_basis_ao_power(self, ao_power):
        rank = 2
        dims = list(range(rank))
        dims[0] = int(self.ao_basis_ao_num)
        dims[1] = int(3)

        dim_max = 1
        for d in dims:
            dim_max *= d
        self.acquire_lock('ao_basis_ao_power')
        try:
            self.write_array_in(self.path_ao_basis, 'ao_power', rank, dims,
                                dim_max, ao_power)
        finally:
            self.release_lock('ao_basis_ao_power')

    ao_basis_ao_power = property(fset=set_ao_basis_ao_power,
                                 fget=get_ao_basis_ao_power)

    def has_ao_basis_ao_power(self):
        return (os.access(self.path_ao_basis + '/ao_power.gz', os.F_OK) == 1)

    def get_ao_basis_ao_prim_num_max(self):
        return maxval(self.ao_basis_ao_prim_num)

    ao_basis_ao_prim_num_max = property(fget=get_ao_basis_ao_prim_num_max)

    def get_ao_basis_ao_coef(self):
        rank = 2
        dims = list(range(rank))
        dims[0] = int(self.ao_basis_ao_num)
        dims[1] = int(self.ao_basis_ao_prim_num_max)

        dim_max = 1
        for d in dims:
            dim_max *= d
        self.acquire_lock('ao_basis_ao_coef')
        try:
            result = self.read_array_re(self.path_ao_basis, 'ao_coef', rank,
                                        dims, dim_max)
        finally:
            self.release_lock('ao_basis_ao_coef')
        return result

    def set_ao_basis_ao_coef(self, ao_coef):
        rank = 2
        dims = list(range(rank))
        dims[0] = int(self.ao_basis_ao_num)
        dims[1] = int(self.ao_basis_ao_prim_num_max)

        dim_max = 1
        for d in dims:
            dim_max *= d
        self.acquire_lock('ao_basis_ao_coef')
        try:
            self.write_array_re(self.path_ao_basis, 'ao_coef', rank, dims,
                                dim_max, ao_coef)
        finally:
            self.release_lock('ao_basis_ao_coef')

    ao_basis_ao_coef = property(fset=set_ao_basis_ao_coef,
                                fget=get_ao_basis_ao_coef)

    def has_ao_basis_ao_coef(self):
        return (os.access(self.path_ao_basis + '/ao_coef.gz', os.F_OK) == 1)

    def get_ao_basis_ao_expo(self):
        rank = 2
        dims = list(range(rank))
        dims[0] = int(self.ao_basis_ao_num)
        dims[1] = int(self.ao_basis_ao_prim_num_max)

        dim_max = 1
        for d in dims:
            dim_max *= d
        self.acquire_lock('ao_basis_ao_expo')
        try:
            result = self.read_array_re(self.path_ao_basis, 'ao_expo', rank,
                                        dims, dim_max)
        finally:
            self.release_lock('ao_basis_ao_expo')
        return result

    def set_ao_basis_ao_expo(self, ao_expo):
        rank = 2
        dims = list(range(rank))
        dims[0] = int(self.ao_basis_ao_num)
        dims[1] = int(self.ao_basis_ao_prim_num_max)

        dim_max = 1
        for d in dims:
            dim_max *= d
        self.acquire_lock('ao_basis_ao_expo')
        try:
            self.write_array_re(self.path_ao_basis, 'ao_expo', rank, dims,
                                dim_max, ao_expo)
        finally:
            self.release_lock('ao_basis_ao_expo')

    ao_basis_ao_expo = property(fset=set_ao_basis_ao_expo,
                                fget=get_ao_basis_ao_expo)

    def has_ao_basis_ao_expo(self):
        return (os.access(self.path_ao_basis + '/ao_expo.gz', os.F_OK) == 1)

    def get_path_nuclei(self):
        result = self.filename.strip() + '/nuclei'
        self.acquire_lock('nuclei')
        try:
            if not self.exists(result):
                self.mkdir(result)
        finally:
            self.release_lock('nuclei')
        return result

    path_nuclei = property(fget=get_path_nuclei)

    def get_nuclei_nucl_num(self):
        self.acquire_lock('nuclei_nucl_num')
        try:
            result = self.read_in(self.path_nuclei, 'nucl_num')
        finally:
            self.release_lock('nuclei_nucl_num')
        return result

    def set_nuclei_nucl_num(self, nucl_num):
        self.acquire_lock('nuclei_nucl_num')
        try:
            self.write_in(self.path_nuclei, 'nucl_num', nucl_num)
        finally:
            self.release_lock('nuclei_nucl_num')

    nuclei_nucl_num = property(fset=set_nuclei_nucl_num,
                               fget=get_nuclei_nucl_num)

    def has_nuclei_nucl_num(self):
        return (os.access(self.path_nuclei + '/nucl_num', os.F_OK) == 1)

    def get_nuclei_nucl_label(self):
        rank = 1
        dims = list(range(rank))
        dims[0] = int(self.nuclei_nucl_num)

        dim_max = 1
        for d in dims:
            dim_max *= d
        self.acquire_lock('nuclei_nucl_label')
        try:
            result = self.read_array_ch(self.path_nuclei, 'nucl_label', rank,
                                        dims, dim_max)
        finally:
            self.release_lock('nuclei_nucl_label')
        return result

    def set_nuclei_nucl_label(self, nucl_label):
        rank = 1
        dims = list(range(rank))
        dims[0] = int(self.nuclei_nucl_num)

        dim_max = 1
        for d in dims:
            dim_max *= d
        self.acquire_lock('nuclei_nucl_label')
        try:
            self.write_array_ch(self.path_nuclei, 'nucl_label', rank, dims,
                                dim_max, nucl_label)
        finally:
            self.release_lock('nuclei_nucl_label')

    nuclei_nucl_label = property(fset=set_nuclei_nucl_label,
                                 fget=get_nuclei_nucl_label)

    def has_nuclei_nucl_label(self):
        return (os.access(self.path_nuclei + '/nucl_label.gz', os.F_OK) == 1)

    def get_nuclei_nucl_charge(self):
        rank = 1
        dims = list(range(rank))
        dims[0] = int(self.nuclei_nucl_num)

        dim_max = 1
        for d in dims:
            dim_max *= d
        self.acquire_lock('nuclei_nucl_charge')
        try:
            result = self.read_array_re(self.path_nuclei, 'nucl_charge', rank,
                                        dims, dim_max)
        finally:
            self.release_lock('nuclei_nucl_charge')
        return result

    def set_nuclei_nucl_charge(self, nucl_charge):
        rank = 1
        dims = list(range(rank))
        dims[0] = int(self.nuclei_nucl_num)

        dim_max = 1
        for d in dims:
            dim_max *= d
        self.acquire_lock('nuclei_nucl_charge')
        try:
            self.write_array_re(self.path_nuclei, 'nucl_charge', rank, dims,
                                dim_max, nucl_charge)
        finally:
            self.release_lock('nuclei_nucl_charge')

    nuclei_nucl_charge = property(fset=set_nuclei_nucl_charge,
                                  fget=get_nuclei_nucl_charge)

    def has_nuclei_nucl_charge(self):
        return (os.access(self.path_nuclei + '/nucl_charge.gz', os.F_OK) == 1)

    def get_nuclei_nucl_coord(self):
        rank = 2
        dims = list(range(rank))
        dims[0] = int(self.nuclei_nucl_num)
        dims[1] = int(3)

        dim_max = 1
        for d in dims:
            dim_max *= d
        self.acquire_lock('nuclei_nucl_coord')
        try:
            result = self.read_array_re(self.path_nuclei, 'nucl_coord', rank,
                                        dims, dim_max)
        finally:
            self.release_lock('nuclei_nucl_coord')
        return result

    def set_nuclei_nucl_coord(self, nucl_coord):
        rank = 2
        dims = list(range(rank))
        dims[0] = int(self.nuclei_nucl_num)
        dims[1] = int(3)

        dim_max = 1
        for d in dims:
            dim_max *= d
        self.acquire_lock('nuclei_nucl_coord')
        try:
            self.write_array_re(self.path_nuclei, 'nucl_coord', rank, dims,
                                dim_max, nucl_coord)
        finally:
            self.release_lock('nuclei_nucl_coord')

    nuclei_nucl_coord = property(fset=set_nuclei_nucl_coord,
                                 fget=get_nuclei_nucl_coord)

    def has_nuclei_nucl_coord(self):
        return (os.access(self.path_nuclei + '/nucl_coord.gz', os.F_OK) == 1)

    def get_path_jastrow(self):
        result = self.filename.strip() + '/jastrow'
        self.acquire_lock('jastrow')
        try:
            if not self.exists(result):
                self.mkdir(result)
        finally:
            self.release_lock('jastrow')
        return result

    path_jastrow = property(fget=get_path_jastrow)

    def get_jastrow_j2e_type(self):
        self.acquire_lock('jastrow_j2e_type')
        try:
            result = self.read_ch(self.path_jastrow, 'j2e_type')
        finally:
            self.release_lock('jastrow_j2e_type')
        return result

    def set_jastrow_j2e_type(self, j2e_type):
        self.acquire_lock('jastrow_j2e_type')
        try:
            self.write_ch(self.path_jastrow, 'j2e_type', j2e_type)
        finally:
            self.release_lock('jastrow_j2e_type')

    jastrow_j2e_type = property(fset=set_jastrow_j2e_type,
                                fget=get_jastrow_j2e_type)

    def has_jastrow_j2e_type(self):
        return (os.access(self.path_jastrow + '/j2e_type', os.F_OK) == 1)

    def get_jastrow_j1e_type(self):
        self.acquire_lock('jastrow_j1e_type')
        try:
            result = self.read_ch(self.path_jastrow, 'j1e_type')
        finally:
            self.release_lock('jastrow_j1e_type')
        return result

    def set_jastrow_j1e_type(self, j1e_type):
        self.acquire_lock('jastrow_j1e_type')
        try:
            self.write_ch(self.path_jastrow, 'j1e_type', j1e_type)
        finally:
            self.release_lock('jastrow_j1e_type')

    jastrow_j1e_type = property(fset=set_jastrow_j1e_type,
                                fget=get_jastrow_j1e_type)

    def has_jastrow_j1e_type(self):
        return (os.access(self.path_jastrow + '/j1e_type', os.F_OK) == 1)

    def get_jastrow_env_type(self):
        self.acquire_lock('jastrow_env_type')
        try:
            result = self.read_ch(self.path_jastrow, 'env_type')
        finally:
            self.release_lock('jastrow_env_type')
        return result

    def set_jastrow_env_type(self, env_type):
        self.acquire_lock('jastrow_env_type')
        try:
            self.write_ch(self.path_jastrow, 'env_type', env_type)
        finally:
            self.release_lock('jastrow_env_type')

    jastrow_env_type = property(fset=set_jastrow_env_type,
                                fget=get_jastrow_env_type)

    def has_jastrow_env_type(self):
        return (os.access(self.path_jastrow + '/env_type', os.F_OK) == 1)

    def get_jastrow_jbh_size(self):
        self.acquire_lock('jastrow_jbh_size')
        try:
            result = self.read_in(self.path_jastrow, 'jbh_size')
        finally:
            self.release_lock('jastrow_jbh_size')
        return result

    def set_jastrow_jbh_size(self, jbh_size):
        self.acquire_lock('jastrow_jbh_size')
        try:
            self.write_in(self.path_jastrow, 'jbh_size', jbh_size)
        finally:
            self.release_lock('jastrow_jbh_size')

    jastrow_jbh_size = property(fset=set_jastrow_jbh_size,
                                fget=get_jastrow_jbh_size)

    def has_jastrow_jbh_size(self):
        return (os.access(self.path_jastrow + '/jbh_size', os.F_OK) == 1)

    def get_jastrow_jbh_ee(self):
        rank = 1
        dims = list(range(rank))
        dims[0] = int(self.nuclei_nucl_num)

        dim_max = 1
        for d in dims:
            dim_max *= d
        self.acquire_lock('jastrow_jbh_ee')
        try:
            result = self.read_array_re(self.path_jastrow, 'jbh_ee', rank,
                                        dims, dim_max)
        finally:
            self.release_lock('jastrow_jbh_ee')
        return result

    def set_jastrow_jbh_ee(self, jbh_ee):
        rank = 1
        dims = list(range(rank))
        dims[0] = int(self.nuclei_nucl_num)

        dim_max = 1
        for d in dims:
            dim_max *= d
        self.acquire_lock('jastrow_jbh_ee')
        try:
            self.write_array_re(self.path_jastrow, 'jbh_ee', rank, dims,
                                dim_max, jbh_ee)
        finally:
            self.release_lock('jastrow_jbh_ee')

    jastrow_jbh_ee = property(fset=set_jastrow_jbh_ee, fget=get_jastrow_jbh_ee)

    def has_jastrow_jbh_ee(self):
        return (os.access(self.path_jastrow + '/jbh_ee.gz', os.F_OK) == 1)

    def get_jastrow_jbh_en(self):
        rank = 1
        dims = list(range(rank))
        dims[0] = int(self.nuclei_nucl_num)

        dim_max = 1
        for d in dims:
            dim_max *= d
        self.acquire_lock('jastrow_jbh_en')
        try:
            result = self.read_array_re(self.path_jastrow, 'jbh_en', rank,
                                        dims, dim_max)
        finally:
            self.release_lock('jastrow_jbh_en')
        return result

    def set_jastrow_jbh_en(self, jbh_en):
        rank = 1
        dims = list(range(rank))
        dims[0] = int(self.nuclei_nucl_num)

        dim_max = 1
        for d in dims:
            dim_max *= d
        self.acquire_lock('jastrow_jbh_en')
        try:
            self.write_array_re(self.path_jastrow, 'jbh_en', rank, dims,
                                dim_max, jbh_en)
        finally:
            self.release_lock('jastrow_jbh_en')

    jastrow_jbh_en = property(fset=set_jastrow_jbh_en, fget=get_jastrow_jbh_en)

    def has_jastrow_jbh_en(self):
        return (os.access(self.path_jastrow + '/jbh_en.gz', os.F_OK) == 1)

    def get_jastrow_jbh_c(self):
        rank = 2
        dims = list(range(rank))
        dims[0] = int(self.jastrow_jbh_size)
        dims[1] = int(self.nuclei_nucl_num)

        dim_max = 1
        for d in dims:
            dim_max *= d
        self.acquire_lock('jastrow_jbh_c')
        try:
            result = self.read_array_re(self.path_jastrow, 'jbh_c', rank, dims,
                                        dim_max)
        finally:
            self.release_lock('jastrow_jbh_c')
        return result

    def set_jastrow_jbh_c(self, jbh_c):
        rank = 2
        dims = list(range(rank))
        dims[0] = int(self.jastrow_jbh_size)
        dims[1] = int(self.nuclei_nucl_num)

        dim_max = 1
        for d in dims:
            dim_max *= d
        self.acquire_lock('jastrow_jbh_c')
        try:
            self.write_array_re(self.path_jastrow, 'jbh_c', rank, dims,
                                dim_max, jbh_c)
        finally:
            self.release_lock('jastrow_jbh_c')

    jastrow_jbh_c = property(fset=set_jastrow_jbh_c, fget=get_jastrow_jbh_c)

    def has_jastrow_jbh_c(self):
        return (os.access(self.path_jastrow + '/jbh_c.gz', os.F_OK) == 1)

    def get_jastrow_jbh_m(self):
        rank = 2
        dims = list(range(rank))
        dims[0] = int(self.jastrow_jbh_size)
        dims[1] = int(self.nuclei_nucl_num)

        dim_max = 1
        for d in dims:
            dim_max *= d
        self.acquire_lock('jastrow_jbh_m')
        try:
            result = self.read_array_in(self.path_jastrow, 'jbh_m', rank, dims,
                                        dim_max)
        finally:
            self.release_lock('jastrow_jbh_m')
        return result

    def set_jastrow_jbh_m(self, jbh_m):
        rank = 2
        dims = list(range(rank))
        dims[0] = int(self.jastrow_jbh_size)
        dims[1] = int(self.nuclei_nucl_num)

        dim_max = 1
        for d in dims:
            dim_max *= d
        self.acquire_lock('jastrow_jbh_m')
        try:
            self.write_array_in(self.path_jastrow, 'jbh_m', rank, dims,
                                dim_max, jbh_m)
        finally:
            self.release_lock('jastrow_jbh_m')

    jastrow_jbh_m = property(fset=set_jastrow_jbh_m, fget=get_jastrow_jbh_m)

    def has_jastrow_jbh_m(self):
        return (os.access(self.path_jastrow + '/jbh_m.gz', os.F_OK) == 1)

    def get_jastrow_jbh_n(self):
        rank = 2
        dims = list(range(rank))
        dims[0] = int(self.jastrow_jbh_size)
        dims[1] = int(self.nuclei_nucl_num)

        dim_max = 1
        for d in dims:
            dim_max *= d
        self.acquire_lock('jastrow_jbh_n')
        try:
            result = self.read_array_in(self.path_jastrow, 'jbh_n', rank, dims,
                                        dim_max)
        finally:
            self.release_lock('jastrow_jbh_n')
        return result

    def set_jastrow_jbh_n(self, jbh_n):
        rank = 2
        dims = list(range(rank))
        dims[0] = int(self.jastrow_jbh_size)
        dims[1] = int(self.nuclei_nucl_num)

        dim_max = 1
        for d in dims:
            dim_max *= d
        self.acquire_lock('jastrow_jbh_n')
        try:
            self.write_array_in(self.path_jastrow, 'jbh_n', rank, dims,
                                dim_max, jbh_n)
        finally:
            self.release_lock('jastrow_jbh_n')

    jastrow_jbh_n = property(fset=set_jastrow_jbh_n, fget=get_jastrow_jbh_n)

    def has_jastrow_jbh_n(self):
        return (os.access(self.path_jastrow + '/jbh_n.gz', os.F_OK) == 1)

    def get_jastrow_jbh_o(self):
        rank = 2
        dims = list(range(rank))
        dims[0] = int(self.jastrow_jbh_size)
        dims[1] = int(self.nuclei_nucl_num)

        dim_max = 1
        for d in dims:
            dim_max *= d
        self.acquire_lock('jastrow_jbh_o')
        try:
            result = self.read_array_in(self.path_jastrow, 'jbh_o', rank, dims,
                                        dim_max)
        finally:
            self.release_lock('jastrow_jbh_o')
        return result

    def set_jastrow_jbh_o(self, jbh_o):
        rank = 2
        dims = list(range(rank))
        dims[0] = int(self.jastrow_jbh_size)
        dims[1] = int(self.nuclei_nucl_num)

        dim_max = 1
        for d in dims:
            dim_max *= d
        self.acquire_lock('jastrow_jbh_o')
        try:
            self.write_array_in(self.path_jastrow, 'jbh_o', rank, dims,
                                dim_max, jbh_o)
        finally:
            self.release_lock('jastrow_jbh_o')

    jastrow_jbh_o = property(fset=set_jastrow_jbh_o, fget=get_jastrow_jbh_o)

    def has_jastrow_jbh_o(self):
        return (os.access(self.path_jastrow + '/jbh_o.gz', os.F_OK) == 1)

    def get_jastrow_a_boys(self):
        self.acquire_lock('jastrow_a_boys')
        try:
            result = self.read_re(self.path_jastrow, 'a_boys')
        finally:
            self.release_lock('jastrow_a_boys')
        return result

    def set_jastrow_a_boys(self, a_boys):
        self.acquire_lock('jastrow_a_boys')
        try:
            self.write_re(self.path_jastrow, 'a_boys', a_boys)
        finally:
            self.release_lock('jastrow_a_boys')

    jastrow_a_boys = property(fset=set_jastrow_a_boys, fget=get_jastrow_a_boys)

    def has_jastrow_a_boys(self):
        return (os.access(self.path_jastrow + '/a_boys', os.F_OK) == 1)

    def get_jastrow_nu_erf(self):
        self.acquire_lock('jastrow_nu_erf')
        try:
            result = self.read_re(self.path_jastrow, 'nu_erf')
        finally:
            self.release_lock('jastrow_nu_erf')
        return result

    def set_jastrow_nu_erf(self, nu_erf):
        self.acquire_lock('jastrow_nu_erf')
        try:
            self.write_re(self.path_jastrow, 'nu_erf', nu_erf)
        finally:
            self.release_lock('jastrow_nu_erf')

    jastrow_nu_erf = property(fset=set_jastrow_nu_erf, fget=get_jastrow_nu_erf)

    def has_jastrow_nu_erf(self):
        return (os.access(self.path_jastrow + '/nu_erf', os.F_OK) == 1)

    def get_jastrow_env_expo(self):
        rank = 1
        dims = list(range(rank))
        dims[0] = int(self.nuclei_nucl_num)

        dim_max = 1
        for d in dims:
            dim_max *= d
        self.acquire_lock('jastrow_env_expo')
        try:
            result = self.read_array_re(self.path_jastrow, 'env_expo', rank,
                                        dims, dim_max)
        finally:
            self.release_lock('jastrow_env_expo')
        return result

    def set_jastrow_env_expo(self, env_expo):
        rank = 1
        dims = list(range(rank))
        dims[0] = int(self.nuclei_nucl_num)

        dim_max = 1
        for d in dims:
            dim_max *= d
        self.acquire_lock('jastrow_env_expo')
        try:
            self.write_array_re(self.path_jastrow, 'env_expo', rank, dims,
                                dim_max, env_expo)
        finally:
            self.release_lock('jastrow_env_expo')

    jastrow_env_expo = property(fset=set_jastrow_env_expo,
                                fget=get_jastrow_env_expo)

    def has_jastrow_env_expo(self):
        return (os.access(self.path_jastrow + '/env_expo.gz', os.F_OK) == 1)

    def get_jastrow_env_coef(self):
        rank = 1
        dims = list(range(rank))
        dims[0] = int(self.nuclei_nucl_num)

        dim_max = 1
        for d in dims:
            dim_max *= d
        self.acquire_lock('jastrow_env_coef')
        try:
            result = self.read_array_re(self.path_jastrow, 'env_coef', rank,
                                        dims, dim_max)
        finally:
            self.release_lock('jastrow_env_coef')
        return result

    def set_jastrow_env_coef(self, env_coef):
        rank = 1
        dims = list(range(rank))
        dims[0] = int(self.nuclei_nucl_num)

        dim_max = 1
        for d in dims:
            dim_max *= d
        self.acquire_lock('jastrow_env_coef')
        try:
            self.write_array_re(self.path_jastrow, 'env_coef', rank, dims,
                                dim_max, env_coef)
        finally:
            self.release_lock('jastrow_env_coef')

    jastrow_env_coef = property(fset=set_jastrow_env_coef,
                                fget=get_jastrow_env_coef)

    def has_jastrow_env_coef(self):
        return (os.access(self.path_jastrow + '/env_coef.gz', os.F_OK) == 1)

    def get_jastrow_j1e_size(self):
        self.acquire_lock('jastrow_j1e_size')
        try:
            result = self.read_in(self.path_jastrow, 'j1e_size')
        finally:
            self.release_lock('jastrow_j1e_size')
        return result

    def set_jastrow_j1e_size(self, j1e_size):
        self.acquire_lock('jastrow_j1e_size')
        try:
            self.write_in(self.path_jastrow, 'j1e_size', j1e_size)
        finally:
            self.release_lock('jastrow_j1e_size')

    jastrow_j1e_size = property(fset=set_jastrow_j1e_size,
                                fget=get_jastrow_j1e_size)

    def has_jastrow_j1e_size(self):
        return (os.access(self.path_jastrow + '/j1e_size', os.F_OK) == 1)

    def get_jastrow_j1e_expo(self):
        rank = 2
        dims = list(range(rank))
        dims[0] = int(self.jastrow_j1e_size)
        dims[1] = int(self.nuclei_nucl_num)

        dim_max = 1
        for d in dims:
            dim_max *= d
        self.acquire_lock('jastrow_j1e_expo')
        try:
            result = self.read_array_re(self.path_jastrow, 'j1e_expo', rank,
                                        dims, dim_max)
        finally:
            self.release_lock('jastrow_j1e_expo')
        return result

    def set_jastrow_j1e_expo(self, j1e_expo):
        rank = 2
        dims = list(range(rank))
        dims[0] = int(self.jastrow_j1e_size)
        dims[1] = int(self.nuclei_nucl_num)

        dim_max = 1
        for d in dims:
            dim_max *= d
        self.acquire_lock('jastrow_j1e_expo')
        try:
            self.write_array_re(self.path_jastrow, 'j1e_expo', rank, dims,
                                dim_max, j1e_expo)
        finally:
            self.release_lock('jastrow_j1e_expo')

    jastrow_j1e_expo = property(fset=set_jastrow_j1e_expo,
                                fget=get_jastrow_j1e_expo)

    def has_jastrow_j1e_expo(self):
        return (os.access(self.path_jastrow + '/j1e_expo.gz', os.F_OK) == 1)

    def get_jastrow_j1e_coef(self):
        rank = 2
        dims = list(range(rank))
        dims[0] = int(self.jastrow_j1e_size)
        dims[1] = int(self.nuclei_nucl_num)

        dim_max = 1
        for d in dims:
            dim_max *= d
        self.acquire_lock('jastrow_j1e_coef')
        try:
            result = self.read_array_re(self.path_jastrow, 'j1e_coef', rank,
                                        dims, dim_max)
        finally:
            self.release_lock('jastrow_j1e_coef')
        return result

    def set_jastrow_j1e_coef(self, j1e_coef):
        rank = 2
        dims = list(range(rank))
        dims[0] = int(self.jastrow_j1e_size)
        dims[1] = int(self.nuclei_nucl_num)

        dim_max = 1
        for d in dims:
            dim_max *= d
        self.acquire_lock('jastrow_j1e_coef')
        try:
            self.write_array_re(self.path_jastrow, 'j1e_coef', rank, dims,
                                dim_max, j1e_coef)
        finally:
            self.release_lock('jastrow_j1e_coef')

    jastrow_j1e_coef = property(fset=set_jastrow_j1e_coef,
                                fget=get_jastrow_j1e_coef)

    def has_jastrow_j1e_coef(self):
        return (os.access(self.path_jastrow + '/j1e_coef.gz', os.F_OK) == 1)

    def get_jastrow_j1e_coef_ao(self):
        rank = 1
        dims = list(range(rank))
        dims[0] = int(self.ao_basis_ao_num)

        dim_max = 1
        for d in dims:
            dim_max *= d
        self.acquire_lock('jastrow_j1e_coef_ao')
        try:
            result = self.read_array_re(self.path_jastrow, 'j1e_coef_ao', rank,
                                        dims, dim_max)
        finally:
            self.release_lock('jastrow_j1e_coef_ao')
        return result

    def set_jastrow_j1e_coef_ao(self, j1e_coef_ao):
        rank = 1
        dims = list(range(rank))
        dims[0] = int(self.ao_basis_ao_num)

        dim_max = 1
        for d in dims:
            dim_max *= d
        self.acquire_lock('jastrow_j1e_coef_ao')
        try:
            self.write_array_re(self.path_jastrow, 'j1e_coef_ao', rank, dims,
                                dim_max, j1e_coef_ao)
        finally:
            self.release_lock('jastrow_j1e_coef_ao')

    jastrow_j1e_coef_ao = property(fset=set_jastrow_j1e_coef_ao,
                                   fget=get_jastrow_j1e_coef_ao)

    def has_jastrow_j1e_coef_ao(self):
        return (os.access(self.path_jastrow + '/j1e_coef_ao.gz', os.F_OK) == 1)

    def get_jastrow_j1e_coef_ao2(self):
        rank = 2
        dims = list(range(rank))
        dims[0] = int(self.ao_basis_ao_num)
        dims[1] = int(self.ao_basis_ao_num)

        dim_max = 1
        for d in dims:
            dim_max *= d
        self.acquire_lock('jastrow_j1e_coef_ao2')
        try:
            result = self.read_array_re(self.path_jastrow, 'j1e_coef_ao2',
                                        rank, dims, dim_max)
        finally:
            self.release_lock('jastrow_j1e_coef_ao2')
        return result

    def set_jastrow_j1e_coef_ao2(self, j1e_coef_ao2):
        rank = 2
        dims = list(range(rank))
        dims[0] = int(self.ao_basis_ao_num)
        dims[1] = int(self.ao_basis_ao_num)

        dim_max = 1
        for d in dims:
            dim_max *= d
        self.acquire_lock('jastrow_j1e_coef_ao2')
        try:
            self.write_array_re(self.path_jastrow, 'j1e_coef_ao2', rank, dims,
                                dim_max, j1e_coef_ao2)
        finally:
            self.release_lock('jastrow_j1e_coef_ao2')

    jastrow_j1e_coef_ao2 = property(fset=set_jastrow_j1e_coef_ao2,
                                    fget=get_jastrow_j1e_coef_ao2)

    def has_jastrow_j1e_coef_ao2(self):
        return (os.access(self.path_jastrow + '/j1e_coef_ao2.gz',
                          os.F_OK) == 1)

    def get_jastrow_mur_type(self):
        self.acquire_lock('jastrow_mur_type')
        try:
            result = self.read_in(self.path_jastrow, 'mur_type')
        finally:
            self.release_lock('jastrow_mur_type')
        return result

    def set_jastrow_mur_type(self, mur_type):
        self.acquire_lock('jastrow_mur_type')
        try:
            self.write_in(self.path_jastrow, 'mur_type', mur_type)
        finally:
            self.release_lock('jastrow_mur_type')

    jastrow_mur_type = property(fset=set_jastrow_mur_type,
                                fget=get_jastrow_mur_type)

    def has_jastrow_mur_type(self):
        return (os.access(self.path_jastrow + '/mur_type', os.F_OK) == 1)

    def get_jastrow_mu_r_ct(self):
        self.acquire_lock('jastrow_mu_r_ct')
        try:
            result = self.read_re(self.path_jastrow, 'mu_r_ct')
        finally:
            self.release_lock('jastrow_mu_r_ct')
        return result

    def set_jastrow_mu_r_ct(self, mu_r_ct):
        self.acquire_lock('jastrow_mu_r_ct')
        try:
            self.write_re(self.path_jastrow, 'mu_r_ct', mu_r_ct)
        finally:
            self.release_lock('jastrow_mu_r_ct')

    jastrow_mu_r_ct = property(fset=set_jastrow_mu_r_ct,
                               fget=get_jastrow_mu_r_ct)

    def has_jastrow_mu_r_ct(self):
        return (os.access(self.path_jastrow + '/mu_r_ct', os.F_OK) == 1)

    def get_jastrow_jpsi_type(self):
        self.acquire_lock('jastrow_jpsi_type')
        try:
            result = self.read_ch(self.path_jastrow, 'jpsi_type')
        finally:
            self.release_lock('jastrow_jpsi_type')
        return result

    def set_jastrow_jpsi_type(self, jpsi_type):
        self.acquire_lock('jastrow_jpsi_type')
        try:
            self.write_ch(self.path_jastrow, 'jpsi_type', jpsi_type)
        finally:
            self.release_lock('jastrow_jpsi_type')

    jastrow_jpsi_type = property(fset=set_jastrow_jpsi_type,
                                 fget=get_jastrow_jpsi_type)

    def has_jastrow_jpsi_type(self):
        return (os.access(self.path_jastrow + '/jpsi_type', os.F_OK) == 1)

    def get_jastrow_inv_sgn_jast(self):
        self.acquire_lock('jastrow_inv_sgn_jast')
        try:
            result = self.read_lo(self.path_jastrow, 'inv_sgn_jast')
        finally:
            self.release_lock('jastrow_inv_sgn_jast')
        return result

    def set_jastrow_inv_sgn_jast(self, inv_sgn_jast):
        self.acquire_lock('jastrow_inv_sgn_jast')
        try:
            self.write_lo(self.path_jastrow, 'inv_sgn_jast', inv_sgn_jast)
        finally:
            self.release_lock('jastrow_inv_sgn_jast')

    jastrow_inv_sgn_jast = property(fset=set_jastrow_inv_sgn_jast,
                                    fget=get_jastrow_inv_sgn_jast)

    def has_jastrow_inv_sgn_jast(self):
        return (os.access(self.path_jastrow + '/inv_sgn_jast', os.F_OK) == 1)

    def get_jastrow_jast_a_up_up(self):
        self.acquire_lock('jastrow_jast_a_up_up')
        try:
            result = self.read_re(self.path_jastrow, 'jast_a_up_up')
        finally:
            self.release_lock('jastrow_jast_a_up_up')
        return result

    def set_jastrow_jast_a_up_up(self, jast_a_up_up):
        self.acquire_lock('jastrow_jast_a_up_up')
        try:
            self.write_re(self.path_jastrow, 'jast_a_up_up', jast_a_up_up)
        finally:
            self.release_lock('jastrow_jast_a_up_up')

    jastrow_jast_a_up_up = property(fset=set_jastrow_jast_a_up_up,
                                    fget=get_jastrow_jast_a_up_up)

    def has_jastrow_jast_a_up_up(self):
        return (os.access(self.path_jastrow + '/jast_a_up_up', os.F_OK) == 1)

    def get_jastrow_jast_a_up_dn(self):
        self.acquire_lock('jastrow_jast_a_up_dn')
        try:
            result = self.read_re(self.path_jastrow, 'jast_a_up_dn')
        finally:
            self.release_lock('jastrow_jast_a_up_dn')
        return result

    def set_jastrow_jast_a_up_dn(self, jast_a_up_dn):
        self.acquire_lock('jastrow_jast_a_up_dn')
        try:
            self.write_re(self.path_jastrow, 'jast_a_up_dn', jast_a_up_dn)
        finally:
            self.release_lock('jastrow_jast_a_up_dn')

    jastrow_jast_a_up_dn = property(fset=set_jastrow_jast_a_up_dn,
                                    fget=get_jastrow_jast_a_up_dn)

    def has_jastrow_jast_a_up_dn(self):
        return (os.access(self.path_jastrow + '/jast_a_up_dn', os.F_OK) == 1)

    def get_jastrow_jast_b_up_up(self):
        self.acquire_lock('jastrow_jast_b_up_up')
        try:
            result = self.read_re(self.path_jastrow, 'jast_b_up_up')
        finally:
            self.release_lock('jastrow_jast_b_up_up')
        return result

    def set_jastrow_jast_b_up_up(self, jast_b_up_up):
        self.acquire_lock('jastrow_jast_b_up_up')
        try:
            self.write_re(self.path_jastrow, 'jast_b_up_up', jast_b_up_up)
        finally:
            self.release_lock('jastrow_jast_b_up_up')

    jastrow_jast_b_up_up = property(fset=set_jastrow_jast_b_up_up,
                                    fget=get_jastrow_jast_b_up_up)

    def has_jastrow_jast_b_up_up(self):
        return (os.access(self.path_jastrow + '/jast_b_up_up', os.F_OK) == 1)

    def get_jastrow_jast_b_up_dn(self):
        self.acquire_lock('jastrow_jast_b_up_dn')
        try:
            result = self.read_re(self.path_jastrow, 'jast_b_up_dn')
        finally:
            self.release_lock('jastrow_jast_b_up_dn')
        return result

    def set_jastrow_jast_b_up_dn(self, jast_b_up_dn):
        self.acquire_lock('jastrow_jast_b_up_dn')
        try:
            self.write_re(self.path_jastrow, 'jast_b_up_dn', jast_b_up_dn)
        finally:
            self.release_lock('jastrow_jast_b_up_dn')

    jastrow_jast_b_up_dn = property(fset=set_jastrow_jast_b_up_dn,
                                    fget=get_jastrow_jast_b_up_dn)

    def has_jastrow_jast_b_up_dn(self):
        return (os.access(self.path_jastrow + '/jast_b_up_dn', os.F_OK) == 1)

    def get_jastrow_jast_pen(self):
        rank = 1
        dims = list(range(rank))
        dims[0] = int(self.nuclei_nucl_num)

        dim_max = 1
        for d in dims:
            dim_max *= d
        self.acquire_lock('jastrow_jast_pen')
        try:
            result = self.read_array_re(self.path_jastrow, 'jast_pen', rank,
                                        dims, dim_max)
        finally:
            self.release_lock('jastrow_jast_pen')
        return result

    def set_jastrow_jast_pen(self, jast_pen):
        rank = 1
        dims = list(range(rank))
        dims[0] = int(self.nuclei_nucl_num)

        dim_max = 1
        for d in dims:
            dim_max *= d
        self.acquire_lock('jastrow_jast_pen')
        try:
            self.write_array_re(self.path_jastrow, 'jast_pen', rank, dims,
                                dim_max, jast_pen)
        finally:
            self.release_lock('jastrow_jast_pen')

    jastrow_jast_pen = property(fset=set_jastrow_jast_pen,
                                fget=get_jastrow_jast_pen)

    def has_jastrow_jast_pen(self):
        return (os.access(self.path_jastrow + '/jast_pen.gz', os.F_OK) == 1)

    def get_jastrow_jast_een_e_a(self):
        rank = 1
        dims = list(range(rank))
        dims[0] = int(self.nuclei_nucl_num)

        dim_max = 1
        for d in dims:
            dim_max *= d
        self.acquire_lock('jastrow_jast_een_e_a')
        try:
            result = self.read_array_re(self.path_jastrow, 'jast_een_e_a',
                                        rank, dims, dim_max)
        finally:
            self.release_lock('jastrow_jast_een_e_a')
        return result

    def set_jastrow_jast_een_e_a(self, jast_een_e_a):
        rank = 1
        dims = list(range(rank))
        dims[0] = int(self.nuclei_nucl_num)

        dim_max = 1
        for d in dims:
            dim_max *= d
        self.acquire_lock('jastrow_jast_een_e_a')
        try:
            self.write_array_re(self.path_jastrow, 'jast_een_e_a', rank, dims,
                                dim_max, jast_een_e_a)
        finally:
            self.release_lock('jastrow_jast_een_e_a')

    jastrow_jast_een_e_a = property(fset=set_jastrow_jast_een_e_a,
                                    fget=get_jastrow_jast_een_e_a)

    def has_jastrow_jast_een_e_a(self):
        return (os.access(self.path_jastrow + '/jast_een_e_a.gz',
                          os.F_OK) == 1)

    def get_jastrow_jast_een_e_b(self):
        rank = 1
        dims = list(range(rank))
        dims[0] = int(self.nuclei_nucl_num)

        dim_max = 1
        for d in dims:
            dim_max *= d
        self.acquire_lock('jastrow_jast_een_e_b')
        try:
            result = self.read_array_re(self.path_jastrow, 'jast_een_e_b',
                                        rank, dims, dim_max)
        finally:
            self.release_lock('jastrow_jast_een_e_b')
        return result

    def set_jastrow_jast_een_e_b(self, jast_een_e_b):
        rank = 1
        dims = list(range(rank))
        dims[0] = int(self.nuclei_nucl_num)

        dim_max = 1
        for d in dims:
            dim_max *= d
        self.acquire_lock('jastrow_jast_een_e_b')
        try:
            self.write_array_re(self.path_jastrow, 'jast_een_e_b', rank, dims,
                                dim_max, jast_een_e_b)
        finally:
            self.release_lock('jastrow_jast_een_e_b')

    jastrow_jast_een_e_b = property(fset=set_jastrow_jast_een_e_b,
                                    fget=get_jastrow_jast_een_e_b)

    def has_jastrow_jast_een_e_b(self):
        return (os.access(self.path_jastrow + '/jast_een_e_b.gz',
                          os.F_OK) == 1)

    def get_jastrow_jast_een_n(self):
        rank = 1
        dims = list(range(rank))
        dims[0] = int(self.nuclei_nucl_num)

        dim_max = 1
        for d in dims:
            dim_max *= d
        self.acquire_lock('jastrow_jast_een_n')
        try:
            result = self.read_array_re(self.path_jastrow, 'jast_een_n', rank,
                                        dims, dim_max)
        finally:
            self.release_lock('jastrow_jast_een_n')
        return result

    def set_jastrow_jast_een_n(self, jast_een_n):
        rank = 1
        dims = list(range(rank))
        dims[0] = int(self.nuclei_nucl_num)

        dim_max = 1
        for d in dims:
            dim_max *= d
        self.acquire_lock('jastrow_jast_een_n')
        try:
            self.write_array_re(self.path_jastrow, 'jast_een_n', rank, dims,
                                dim_max, jast_een_n)
        finally:
            self.release_lock('jastrow_jast_een_n')

    jastrow_jast_een_n = property(fset=set_jastrow_jast_een_n,
                                  fget=get_jastrow_jast_een_n)

    def has_jastrow_jast_een_n(self):
        return (os.access(self.path_jastrow + '/jast_een_n.gz', os.F_OK) == 1)

    def get_jastrow_jast_core_a1(self):
        rank = 1
        dims = list(range(rank))
        dims[0] = int(self.nuclei_nucl_num)

        dim_max = 1
        for d in dims:
            dim_max *= d
        self.acquire_lock('jastrow_jast_core_a1')
        try:
            result = self.read_array_re(self.path_jastrow, 'jast_core_a1',
                                        rank, dims, dim_max)
        finally:
            self.release_lock('jastrow_jast_core_a1')
        return result

    def set_jastrow_jast_core_a1(self, jast_core_a1):
        rank = 1
        dims = list(range(rank))
        dims[0] = int(self.nuclei_nucl_num)

        dim_max = 1
        for d in dims:
            dim_max *= d
        self.acquire_lock('jastrow_jast_core_a1')
        try:
            self.write_array_re(self.path_jastrow, 'jast_core_a1', rank, dims,
                                dim_max, jast_core_a1)
        finally:
            self.release_lock('jastrow_jast_core_a1')

    jastrow_jast_core_a1 = property(fset=set_jastrow_jast_core_a1,
                                    fget=get_jastrow_jast_core_a1)

    def has_jastrow_jast_core_a1(self):
        return (os.access(self.path_jastrow + '/jast_core_a1.gz',
                          os.F_OK) == 1)

    def get_jastrow_jast_core_a2(self):
        rank = 1
        dims = list(range(rank))
        dims[0] = int(self.nuclei_nucl_num)

        dim_max = 1
        for d in dims:
            dim_max *= d
        self.acquire_lock('jastrow_jast_core_a2')
        try:
            result = self.read_array_re(self.path_jastrow, 'jast_core_a2',
                                        rank, dims, dim_max)
        finally:
            self.release_lock('jastrow_jast_core_a2')
        return result

    def set_jastrow_jast_core_a2(self, jast_core_a2):
        rank = 1
        dims = list(range(rank))
        dims[0] = int(self.nuclei_nucl_num)

        dim_max = 1
        for d in dims:
            dim_max *= d
        self.acquire_lock('jastrow_jast_core_a2')
        try:
            self.write_array_re(self.path_jastrow, 'jast_core_a2', rank, dims,
                                dim_max, jast_core_a2)
        finally:
            self.release_lock('jastrow_jast_core_a2')

    jastrow_jast_core_a2 = property(fset=set_jastrow_jast_core_a2,
                                    fget=get_jastrow_jast_core_a2)

    def has_jastrow_jast_core_a2(self):
        return (os.access(self.path_jastrow + '/jast_core_a2.gz',
                          os.F_OK) == 1)

    def get_jastrow_jast_core_b1(self):
        rank = 1
        dims = list(range(rank))
        dims[0] = int(self.nuclei_nucl_num)

        dim_max = 1
        for d in dims:
            dim_max *= d
        self.acquire_lock('jastrow_jast_core_b1')
        try:
            result = self.read_array_re(self.path_jastrow, 'jast_core_b1',
                                        rank, dims, dim_max)
        finally:
            self.release_lock('jastrow_jast_core_b1')
        return result

    def set_jastrow_jast_core_b1(self, jast_core_b1):
        rank = 1
        dims = list(range(rank))
        dims[0] = int(self.nuclei_nucl_num)

        dim_max = 1
        for d in dims:
            dim_max *= d
        self.acquire_lock('jastrow_jast_core_b1')
        try:
            self.write_array_re(self.path_jastrow, 'jast_core_b1', rank, dims,
                                dim_max, jast_core_b1)
        finally:
            self.release_lock('jastrow_jast_core_b1')

    jastrow_jast_core_b1 = property(fset=set_jastrow_jast_core_b1,
                                    fget=get_jastrow_jast_core_b1)

    def has_jastrow_jast_core_b1(self):
        return (os.access(self.path_jastrow + '/jast_core_b1.gz',
                          os.F_OK) == 1)

    def get_jastrow_jast_core_b2(self):
        rank = 1
        dims = list(range(rank))
        dims[0] = int(self.nuclei_nucl_num)

        dim_max = 1
        for d in dims:
            dim_max *= d
        self.acquire_lock('jastrow_jast_core_b2')
        try:
            result = self.read_array_re(self.path_jastrow, 'jast_core_b2',
                                        rank, dims, dim_max)
        finally:
            self.release_lock('jastrow_jast_core_b2')
        return result

    def set_jastrow_jast_core_b2(self, jast_core_b2):
        rank = 1
        dims = list(range(rank))
        dims[0] = int(self.nuclei_nucl_num)

        dim_max = 1
        for d in dims:
            dim_max *= d
        self.acquire_lock('jastrow_jast_core_b2')
        try:
            self.write_array_re(self.path_jastrow, 'jast_core_b2', rank, dims,
                                dim_max, jast_core_b2)
        finally:
            self.release_lock('jastrow_jast_core_b2')

    jastrow_jast_core_b2 = property(fset=set_jastrow_jast_core_b2,
                                    fget=get_jastrow_jast_core_b2)

    def has_jastrow_jast_core_b2(self):
        return (os.access(self.path_jastrow + '/jast_core_b2.gz',
                          os.F_OK) == 1)

    def get_jastrow_jast_qmckl_type_nucl_num(self):
        self.acquire_lock('jastrow_jast_qmckl_type_nucl_num')
        try:
            result = self.read_in(self.path_jastrow,
                                  'jast_qmckl_type_nucl_num')
        finally:
            self.release_lock('jastrow_jast_qmckl_type_nucl_num')
        return result

    def set_jastrow_jast_qmckl_type_nucl_num(self, jast_qmckl_type_nucl_num):
        self.acquire_lock('jastrow_jast_qmckl_type_nucl_num')
        try:
            self.write_in(self.path_jastrow, 'jast_qmckl_type_nucl_num',
                          jast_qmckl_type_nucl_num)
        finally:
            self.release_lock('jastrow_jast_qmckl_type_nucl_num')

    jastrow_jast_qmckl_type_nucl_num = property(
        fset=set_jastrow_jast_qmckl_type_nucl_num,
        fget=get_jastrow_jast_qmckl_type_nucl_num)

    def has_jastrow_jast_qmckl_type_nucl_num(self):
        return (os.access(self.path_jastrow + '/jast_qmckl_type_nucl_num',
                          os.F_OK) == 1)

    def get_jastrow_jast_qmckl_type_nucl_vector(self):
        rank = 1
        dims = list(range(rank))
        dims[0] = int(self.nuclei_nucl_num)

        dim_max = 1
        for d in dims:
            dim_max *= d
        self.acquire_lock('jastrow_jast_qmckl_type_nucl_vector')
        try:
            result = self.read_array_in(self.path_jastrow,
                                        'jast_qmckl_type_nucl_vector', rank,
                                        dims, dim_max)
        finally:
            self.release_lock('jastrow_jast_qmckl_type_nucl_vector')
        return result

    def set_jastrow_jast_qmckl_type_nucl_vector(self,
                                                jast_qmckl_type_nucl_vector):
        rank = 1
        dims = list(range(rank))
        dims[0] = int(self.nuclei_nucl_num)

        dim_max = 1
        for d in dims:
            dim_max *= d
        self.acquire_lock('jastrow_jast_qmckl_type_nucl_vector')
        try:
            self.write_array_in(self.path_jastrow,
                                'jast_qmckl_type_nucl_vector', rank, dims,
                                dim_max, jast_qmckl_type_nucl_vector)
        finally:
            self.release_lock('jastrow_jast_qmckl_type_nucl_vector')

    jastrow_jast_qmckl_type_nucl_vector = property(
        fset=set_jastrow_jast_qmckl_type_nucl_vector,
        fget=get_jastrow_jast_qmckl_type_nucl_vector)

    def has_jastrow_jast_qmckl_type_nucl_vector(self):
        return (os.access(
            self.path_jastrow + '/jast_qmckl_type_nucl_vector.gz',
            os.F_OK) == 1)

    def get_jastrow_jast_qmckl_rescale_ee(self):
        self.acquire_lock('jastrow_jast_qmckl_rescale_ee')
        try:
            result = self.read_do(self.path_jastrow, 'jast_qmckl_rescale_ee')
        finally:
            self.release_lock('jastrow_jast_qmckl_rescale_ee')
        return result

    def set_jastrow_jast_qmckl_rescale_ee(self, jast_qmckl_rescale_ee):
        self.acquire_lock('jastrow_jast_qmckl_rescale_ee')
        try:
            self.write_do(self.path_jastrow, 'jast_qmckl_rescale_ee',
                          jast_qmckl_rescale_ee)
        finally:
            self.release_lock('jastrow_jast_qmckl_rescale_ee')

    jastrow_jast_qmckl_rescale_ee = property(
        fset=set_jastrow_jast_qmckl_rescale_ee,
        fget=get_jastrow_jast_qmckl_rescale_ee)

    def has_jastrow_jast_qmckl_rescale_ee(self):
        return (os.access(self.path_jastrow + '/jast_qmckl_rescale_ee',
                          os.F_OK) == 1)

    def get_jastrow_jast_qmckl_rescale_en(self):
        rank = 1
        dims = list(range(rank))
        dims[0] = int(self.jastrow_jast_qmckl_type_nucl_num)

        dim_max = 1
        for d in dims:
            dim_max *= d
        self.acquire_lock('jastrow_jast_qmckl_rescale_en')
        try:
            result = self.read_array_do(self.path_jastrow,
                                        'jast_qmckl_rescale_en', rank, dims,
                                        dim_max)
        finally:
            self.release_lock('jastrow_jast_qmckl_rescale_en')
        return result

    def set_jastrow_jast_qmckl_rescale_en(self, jast_qmckl_rescale_en):
        rank = 1
        dims = list(range(rank))
        dims[0] = int(self.jastrow_jast_qmckl_type_nucl_num)

        dim_max = 1
        for d in dims:
            dim_max *= d
        self.acquire_lock('jastrow_jast_qmckl_rescale_en')
        try:
            self.write_array_do(self.path_jastrow, 'jast_qmckl_rescale_en',
                                rank, dims, dim_max, jast_qmckl_rescale_en)
        finally:
            self.release_lock('jastrow_jast_qmckl_rescale_en')

    jastrow_jast_qmckl_rescale_en = property(
        fset=set_jastrow_jast_qmckl_rescale_en,
        fget=get_jastrow_jast_qmckl_rescale_en)

    def has_jastrow_jast_qmckl_rescale_en(self):
        return (os.access(self.path_jastrow + '/jast_qmckl_rescale_en.gz',
                          os.F_OK) == 1)

    def get_jastrow_jast_qmckl_aord_num(self):
        self.acquire_lock('jastrow_jast_qmckl_aord_num')
        try:
            result = self.read_in(self.path_jastrow, 'jast_qmckl_aord_num')
        finally:
            self.release_lock('jastrow_jast_qmckl_aord_num')
        return result

    def set_jastrow_jast_qmckl_aord_num(self, jast_qmckl_aord_num):
        self.acquire_lock('jastrow_jast_qmckl_aord_num')
        try:
            self.write_in(self.path_jastrow, 'jast_qmckl_aord_num',
                          jast_qmckl_aord_num)
        finally:
            self.release_lock('jastrow_jast_qmckl_aord_num')

    jastrow_jast_qmckl_aord_num = property(
        fset=set_jastrow_jast_qmckl_aord_num,
        fget=get_jastrow_jast_qmckl_aord_num)

    def has_jastrow_jast_qmckl_aord_num(self):
        return (os.access(self.path_jastrow + '/jast_qmckl_aord_num',
                          os.F_OK) == 1)

    def get_jastrow_jast_qmckl_bord_num(self):
        self.acquire_lock('jastrow_jast_qmckl_bord_num')
        try:
            result = self.read_in(self.path_jastrow, 'jast_qmckl_bord_num')
        finally:
            self.release_lock('jastrow_jast_qmckl_bord_num')
        return result

    def set_jastrow_jast_qmckl_bord_num(self, jast_qmckl_bord_num):
        self.acquire_lock('jastrow_jast_qmckl_bord_num')
        try:
            self.write_in(self.path_jastrow, 'jast_qmckl_bord_num',
                          jast_qmckl_bord_num)
        finally:
            self.release_lock('jastrow_jast_qmckl_bord_num')

    jastrow_jast_qmckl_bord_num = property(
        fset=set_jastrow_jast_qmckl_bord_num,
        fget=get_jastrow_jast_qmckl_bord_num)

    def has_jastrow_jast_qmckl_bord_num(self):
        return (os.access(self.path_jastrow + '/jast_qmckl_bord_num',
                          os.F_OK) == 1)

    def get_jastrow_jast_qmckl_cord_num(self):
        self.acquire_lock('jastrow_jast_qmckl_cord_num')
        try:
            result = self.read_in(self.path_jastrow, 'jast_qmckl_cord_num')
        finally:
            self.release_lock('jastrow_jast_qmckl_cord_num')
        return result

    def set_jastrow_jast_qmckl_cord_num(self, jast_qmckl_cord_num):
        self.acquire_lock('jastrow_jast_qmckl_cord_num')
        try:
            self.write_in(self.path_jastrow, 'jast_qmckl_cord_num',
                          jast_qmckl_cord_num)
        finally:
            self.release_lock('jastrow_jast_qmckl_cord_num')

    jastrow_jast_qmckl_cord_num = property(
        fset=set_jastrow_jast_qmckl_cord_num,
        fget=get_jastrow_jast_qmckl_cord_num)

    def has_jastrow_jast_qmckl_cord_num(self):
        return (os.access(self.path_jastrow + '/jast_qmckl_cord_num',
                          os.F_OK) == 1)

    def get_jastrow_jast_qmckl_a_vector(self):
        rank = 1
        dims = list(range(rank))
        dims[0] = int(self.jastrow_jast_qmckl_type_nucl_num *
                      self.jastrow_jast_qmckl_aord_num +
                      self.jastrow_jast_qmckl_type_nucl_num)

        dim_max = 1
        for d in dims:
            dim_max *= d
        self.acquire_lock('jastrow_jast_qmckl_a_vector')
        try:
            result = self.read_array_do(self.path_jastrow,
                                        'jast_qmckl_a_vector', rank, dims,
                                        dim_max)
        finally:
            self.release_lock('jastrow_jast_qmckl_a_vector')
        return result

    def set_jastrow_jast_qmckl_a_vector(self, jast_qmckl_a_vector):
        rank = 1
        dims = list(range(rank))
        dims[0] = int(self.jastrow_jast_qmckl_type_nucl_num *
                      self.jastrow_jast_qmckl_aord_num +
                      self.jastrow_jast_qmckl_type_nucl_num)

        dim_max = 1
        for d in dims:
            dim_max *= d
        self.acquire_lock('jastrow_jast_qmckl_a_vector')
        try:
            self.write_array_do(self.path_jastrow, 'jast_qmckl_a_vector', rank,
                                dims, dim_max, jast_qmckl_a_vector)
        finally:
            self.release_lock('jastrow_jast_qmckl_a_vector')

    jastrow_jast_qmckl_a_vector = property(
        fset=set_jastrow_jast_qmckl_a_vector,
        fget=get_jastrow_jast_qmckl_a_vector)

    def has_jastrow_jast_qmckl_a_vector(self):
        return (os.access(self.path_jastrow + '/jast_qmckl_a_vector.gz',
                          os.F_OK) == 1)

    def get_jastrow_jast_qmckl_b_vector(self):
        rank = 1
        dims = list(range(rank))
        dims[0] = int(self.jastrow_jast_qmckl_bord_num + 1)

        dim_max = 1
        for d in dims:
            dim_max *= d
        self.acquire_lock('jastrow_jast_qmckl_b_vector')
        try:
            result = self.read_array_do(self.path_jastrow,
                                        'jast_qmckl_b_vector', rank, dims,
                                        dim_max)
        finally:
            self.release_lock('jastrow_jast_qmckl_b_vector')
        return result

    def set_jastrow_jast_qmckl_b_vector(self, jast_qmckl_b_vector):
        rank = 1
        dims = list(range(rank))
        dims[0] = int(self.jastrow_jast_qmckl_bord_num + 1)

        dim_max = 1
        for d in dims:
            dim_max *= d
        self.acquire_lock('jastrow_jast_qmckl_b_vector')
        try:
            self.write_array_do(self.path_jastrow, 'jast_qmckl_b_vector', rank,
                                dims, dim_max, jast_qmckl_b_vector)
        finally:
            self.release_lock('jastrow_jast_qmckl_b_vector')

    jastrow_jast_qmckl_b_vector = property(
        fset=set_jastrow_jast_qmckl_b_vector,
        fget=get_jastrow_jast_qmckl_b_vector)

    def has_jastrow_jast_qmckl_b_vector(self):
        return (os.access(self.path_jastrow + '/jast_qmckl_b_vector.gz',
                          os.F_OK) == 1)

    def get_jastrow_jast_qmckl_c_vector_size(self):
        self.acquire_lock('jastrow_jast_qmckl_c_vector_size')
        try:
            result = self.read_in(self.path_jastrow,
                                  'jast_qmckl_c_vector_size')
        finally:
            self.release_lock('jastrow_jast_qmckl_c_vector_size')
        return result

    def set_jastrow_jast_qmckl_c_vector_size(self, jast_qmckl_c_vector_size):
        self.acquire_lock('jastrow_jast_qmckl_c_vector_size')
        try:
            self.write_in(self.path_jastrow, 'jast_qmckl_c_vector_size',
                          jast_qmckl_c_vector_size)
        finally:
            self.release_lock('jastrow_jast_qmckl_c_vector_size')

    jastrow_jast_qmckl_c_vector_size = property(
        fset=set_jastrow_jast_qmckl_c_vector_size,
        fget=get_jastrow_jast_qmckl_c_vector_size)

    def has_jastrow_jast_qmckl_c_vector_size(self):
        return (os.access(self.path_jastrow + '/jast_qmckl_c_vector_size',
                          os.F_OK) == 1)

    def get_jastrow_jast_qmckl_c_vector(self):
        rank = 1
        dims = list(range(rank))
        dims[0] = int(self.jastrow_jast_qmckl_c_vector_size)

        dim_max = 1
        for d in dims:
            dim_max *= d
        self.acquire_lock('jastrow_jast_qmckl_c_vector')
        try:
            result = self.read_array_do(self.path_jastrow,
                                        'jast_qmckl_c_vector', rank, dims,
                                        dim_max)
        finally:
            self.release_lock('jastrow_jast_qmckl_c_vector')
        return result

    def set_jastrow_jast_qmckl_c_vector(self, jast_qmckl_c_vector):
        rank = 1
        dims = list(range(rank))
        dims[0] = int(self.jastrow_jast_qmckl_c_vector_size)

        dim_max = 1
        for d in dims:
            dim_max *= d
        self.acquire_lock('jastrow_jast_qmckl_c_vector')
        try:
            self.write_array_do(self.path_jastrow, 'jast_qmckl_c_vector', rank,
                                dims, dim_max, jast_qmckl_c_vector)
        finally:
            self.release_lock('jastrow_jast_qmckl_c_vector')

    jastrow_jast_qmckl_c_vector = property(
        fset=set_jastrow_jast_qmckl_c_vector,
        fget=get_jastrow_jast_qmckl_c_vector)

    def has_jastrow_jast_qmckl_c_vector(self):
        return (os.access(self.path_jastrow + '/jast_qmckl_c_vector.gz',
                          os.F_OK) == 1)

    def read_i8(self, dir, fil):
        conv = get_conv('i8')
        l_filename = dir.strip() + '/' + fil
        try:
            file = open(l_filename, 'r')
        except IOError:
            self.error('read_i8',
                       'Attribute ' + dir.strip() + '/' + fil + ' is not set')
        dat = file.readline().strip()
        try:
            dat = conv(dat)
        except SyntaxError:
            pass
        file.close()
        return dat

    def write_i8(self, dir, fil, dat):
        if self.read_only:
            self.error('Read-only file.')
        conv = get_conv('i8')
        l_filename = [dir.strip() + '/.' + fil]
        l_filename += [dir.strip() + '/' + fil]
        dat = conv(dat)
        file = open(l_filename[0], 'w')
        print('%20d' % (dat, ), file=file)
        file.close()
        os.rename(l_filename[0], l_filename[1])

    def read_array_i8(self, dir, fil, rank, dims, dim_max):
        l_filename = dir.strip() + '/' + fil + '.gz'
        conv = get_conv('i8')
        try:
            file = GzipFile(filename=l_filename, mode='rb')
            lines = file.read().splitlines()
            rank_read = int(lines[0])
            assert (rank_read == rank)

            dims_read = map(int, lines[1].split())

            for i, j in zip(dims_read, dims):
                assert i == j

            lines.pop(0)
            lines.pop(0)
            dat = map(conv, lines)

            file.close()
            return reshape(dat, dims)

        except IOError:
            self.error('read_array_i8',
                       'Attribute ' + l_filename + ' is not set')

    def write_array_i8(self, dir, fil, rank, dims, dim_max, dat):
        if self.read_only:
            self.error('Read-only file.')
        l_filename = [
            tempfile.mktemp(dir=dir.strip()),
            dir.strip() + '/' + fil + '.gz'
        ]
        try:
            file = StringIO.StringIO()
            file.write('%3d\n' % (rank, ))
            for d in dims:
                file.write('%20d ' % (d, ))
            file.write('\n')

            dat = flatten(dat)
            for i in range(dim_max):
                file.write('%20d\n' % (dat[i], ))
            file.flush()
            buffer = file.getvalue()
            file.close()
            file = GzipFile(filename=l_filename[0], mode='wb')
            file.write(buffer.encode())
            file.close()
            os.rename(l_filename[0], l_filename[1])
        except:
            self.error('write_array_i8', 'Unable to write ' + l_filename[1])

    def read_in(self, dir, fil):
        conv = get_conv('in')
        l_filename = dir.strip() + '/' + fil
        try:
            file = open(l_filename, 'r')
        except IOError:
            self.error('read_in',
                       'Attribute ' + dir.strip() + '/' + fil + ' is not set')
        dat = file.readline().strip()
        try:
            dat = conv(dat)
        except SyntaxError:
            pass
        file.close()
        return dat

    def write_in(self, dir, fil, dat):
        if self.read_only:
            self.error('Read-only file.')
        conv = get_conv('in')
        l_filename = [dir.strip() + '/.' + fil]
        l_filename += [dir.strip() + '/' + fil]
        dat = conv(dat)
        file = open(l_filename[0], 'w')
        print('%20d' % (dat, ), file=file)
        file.close()
        os.rename(l_filename[0], l_filename[1])

    def read_array_in(self, dir, fil, rank, dims, dim_max):
        l_filename = dir.strip() + '/' + fil + '.gz'
        conv = get_conv('in')
        try:
            file = GzipFile(filename=l_filename, mode='rb')
            lines = file.read().splitlines()
            rank_read = int(lines[0])
            assert (rank_read == rank)

            dims_read = map(int, lines[1].split())

            for i, j in zip(dims_read, dims):
                assert i == j

            lines.pop(0)
            lines.pop(0)
            dat = map(conv, lines)

            file.close()
            return reshape(dat, dims)

        except IOError:
            self.error('read_array_in',
                       'Attribute ' + l_filename + ' is not set')

    def write_array_in(self, dir, fil, rank, dims, dim_max, dat):
        if self.read_only:
            self.error('Read-only file.')
        l_filename = [
            tempfile.mktemp(dir=dir.strip()),
            dir.strip() + '/' + fil + '.gz'
        ]
        try:
            file = StringIO.StringIO()
            file.write('%3d\n' % (rank, ))
            for d in dims:
                file.write('%20d ' % (d, ))
            file.write('\n')

            dat = flatten(dat)
            for i in range(dim_max):
                file.write('%20d\n' % (dat[i], ))
            file.flush()
            buffer = file.getvalue()
            file.close()
            file = GzipFile(filename=l_filename[0], mode='wb')
            file.write(buffer.encode())
            file.close()
            os.rename(l_filename[0], l_filename[1])
        except:
            self.error('write_array_in', 'Unable to write ' + l_filename[1])

    def read_re(self, dir, fil):
        conv = get_conv('re')
        l_filename = dir.strip() + '/' + fil
        try:
            file = open(l_filename, 'r')
        except IOError:
            self.error('read_re',
                       'Attribute ' + dir.strip() + '/' + fil + ' is not set')
        dat = file.readline().strip()
        try:
            dat = conv(dat)
        except SyntaxError:
            pass
        file.close()
        return dat

    def write_re(self, dir, fil, dat):
        if self.read_only:
            self.error('Read-only file.')
        conv = get_conv('re')
        l_filename = [dir.strip() + '/.' + fil]
        l_filename += [dir.strip() + '/' + fil]
        dat = conv(dat)
        file = open(l_filename[0], 'w')
        print('%24.15E' % (dat, ), file=file)
        file.close()
        os.rename(l_filename[0], l_filename[1])

    def read_array_re(self, dir, fil, rank, dims, dim_max):
        l_filename = dir.strip() + '/' + fil + '.gz'
        conv = get_conv('re')
        try:
            file = GzipFile(filename=l_filename, mode='rb')
            lines = file.read().splitlines()
            rank_read = int(lines[0])
            assert (rank_read == rank)

            dims_read = map(int, lines[1].split())

            for i, j in zip(dims_read, dims):
                assert i == j

            lines.pop(0)
            lines.pop(0)
            dat = map(conv, lines)

            file.close()
            return reshape(dat, dims)

        except IOError:
            self.error('read_array_re',
                       'Attribute ' + l_filename + ' is not set')

    def write_array_re(self, dir, fil, rank, dims, dim_max, dat):
        if self.read_only:
            self.error('Read-only file.')
        l_filename = [
            tempfile.mktemp(dir=dir.strip()),
            dir.strip() + '/' + fil + '.gz'
        ]
        try:
            file = StringIO.StringIO()
            file.write('%3d\n' % (rank, ))
            for d in dims:
                file.write('%20d ' % (d, ))
            file.write('\n')

            dat = flatten(dat)
            for i in range(dim_max):
                file.write('%24.15E\n' % (dat[i], ))
            file.flush()
            buffer = file.getvalue()
            file.close()
            file = GzipFile(filename=l_filename[0], mode='wb')
            file.write(buffer.encode())
            file.close()
            os.rename(l_filename[0], l_filename[1])
        except:
            self.error('write_array_re', 'Unable to write ' + l_filename[1])

    def read_do(self, dir, fil):
        conv = get_conv('do')
        l_filename = dir.strip() + '/' + fil
        try:
            file = open(l_filename, 'r')
        except IOError:
            self.error('read_do',
                       'Attribute ' + dir.strip() + '/' + fil + ' is not set')
        dat = file.readline().strip()
        try:
            dat = conv(dat)
        except SyntaxError:
            pass
        file.close()
        return dat

    def write_do(self, dir, fil, dat):
        if self.read_only:
            self.error('Read-only file.')
        conv = get_conv('do')
        l_filename = [dir.strip() + '/.' + fil]
        l_filename += [dir.strip() + '/' + fil]
        dat = conv(dat)
        file = open(l_filename[0], 'w')
        print('%24.15E' % (dat, ), file=file)
        file.close()
        os.rename(l_filename[0], l_filename[1])

    def read_array_do(self, dir, fil, rank, dims, dim_max):
        l_filename = dir.strip() + '/' + fil + '.gz'
        conv = get_conv('do')
        try:
            file = GzipFile(filename=l_filename, mode='rb')
            lines = file.read().splitlines()
            rank_read = int(lines[0])
            assert (rank_read == rank)

            dims_read = map(int, lines[1].split())

            for i, j in zip(dims_read, dims):
                assert i == j

            lines.pop(0)
            lines.pop(0)
            dat = map(conv, lines)

            file.close()
            return reshape(dat, dims)

        except IOError:
            self.error('read_array_do',
                       'Attribute ' + l_filename + ' is not set')

    def write_array_do(self, dir, fil, rank, dims, dim_max, dat):
        if self.read_only:
            self.error('Read-only file.')
        l_filename = [
            tempfile.mktemp(dir=dir.strip()),
            dir.strip() + '/' + fil + '.gz'
        ]
        try:
            file = StringIO.StringIO()
            file.write('%3d\n' % (rank, ))
            for d in dims:
                file.write('%20d ' % (d, ))
            file.write('\n')

            dat = flatten(dat)
            for i in range(dim_max):
                file.write('%24.15E\n' % (dat[i], ))
            file.flush()
            buffer = file.getvalue()
            file.close()
            file = GzipFile(filename=l_filename[0], mode='wb')
            file.write(buffer.encode())
            file.close()
            os.rename(l_filename[0], l_filename[1])
        except:
            self.error('write_array_do', 'Unable to write ' + l_filename[1])

    def read_lo(self, dir, fil):
        conv = get_conv('lo')
        l_filename = dir.strip() + '/' + fil
        try:
            file = open(l_filename, 'r')
        except IOError:
            self.error('read_lo',
                       'Attribute ' + dir.strip() + '/' + fil + ' is not set')
        dat = file.readline().strip()
        try:
            dat = conv(dat)
        except SyntaxError:
            pass
        file.close()
        return dat

    def write_lo(self, dir, fil, dat):
        if self.read_only:
            self.error('Read-only file.')
        conv = get_conv('lo')
        l_filename = [dir.strip() + '/.' + fil]
        l_filename += [dir.strip() + '/' + fil]
        dat = conv(dat)
        file = open(l_filename[0], 'w')
        print('%c' % (dat, ), file=file)
        file.close()
        os.rename(l_filename[0], l_filename[1])

    def read_array_lo(self, dir, fil, rank, dims, dim_max):
        l_filename = dir.strip() + '/' + fil + '.gz'
        conv = get_conv('lo')
        try:
            file = GzipFile(filename=l_filename, mode='rb')
            lines = file.read().splitlines()
            rank_read = int(lines[0])
            assert (rank_read == rank)

            dims_read = map(int, lines[1].split())

            for i, j in zip(dims_read, dims):
                assert i == j

            lines.pop(0)
            lines.pop(0)
            dat = map(conv, lines)

            file.close()
            return reshape(dat, dims)

        except IOError:
            self.error('read_array_lo',
                       'Attribute ' + l_filename + ' is not set')

    def write_array_lo(self, dir, fil, rank, dims, dim_max, dat):
        if self.read_only:
            self.error('Read-only file.')
        l_filename = [
            tempfile.mktemp(dir=dir.strip()),
            dir.strip() + '/' + fil + '.gz'
        ]
        try:
            file = StringIO.StringIO()
            file.write('%3d\n' % (rank, ))
            for d in dims:
                file.write('%20d ' % (d, ))
            file.write('\n')

            dat = flatten(dat)
            for i in range(dim_max):
                file.write('%c\n' % (dat[i], ))
            file.flush()
            buffer = file.getvalue()
            file.close()
            file = GzipFile(filename=l_filename[0], mode='wb')
            file.write(buffer.encode())
            file.close()
            os.rename(l_filename[0], l_filename[1])
        except:
            self.error('write_array_lo', 'Unable to write ' + l_filename[1])

    def read_ch(self, dir, fil):
        conv = get_conv('ch')
        l_filename = dir.strip() + '/' + fil
        try:
            file = open(l_filename, 'r')
        except IOError:
            self.error('read_ch',
                       'Attribute ' + dir.strip() + '/' + fil + ' is not set')
        dat = file.readline().strip()
        try:
            dat = conv(dat)
        except SyntaxError:
            pass
        file.close()
        return dat

    def write_ch(self, dir, fil, dat):
        if self.read_only:
            self.error('Read-only file.')
        conv = get_conv('ch')
        l_filename = [dir.strip() + '/.' + fil]
        l_filename += [dir.strip() + '/' + fil]
        dat = conv(dat)
        file = open(l_filename[0], 'w')
        print('%s' % (dat, ), file=file)
        file.close()
        os.rename(l_filename[0], l_filename[1])

    def read_array_ch(self, dir, fil, rank, dims, dim_max):
        l_filename = dir.strip() + '/' + fil + '.gz'
        conv = get_conv('ch')
        try:
            file = GzipFile(filename=l_filename, mode='rb')
            lines = file.read().splitlines()
            rank_read = int(lines[0])
            assert (rank_read == rank)

            dims_read = map(int, lines[1].split())

            for i, j in zip(dims_read, dims):
                assert i == j

            lines.pop(0)
            lines.pop(0)
            dat = map(conv, lines)

            file.close()
            return reshape(dat, dims)

        except IOError:
            self.error('read_array_ch',
                       'Attribute ' + l_filename + ' is not set')

    def write_array_ch(self, dir, fil, rank, dims, dim_max, dat):
        if self.read_only:
            self.error('Read-only file.')
        l_filename = [
            tempfile.mktemp(dir=dir.strip()),
            dir.strip() + '/' + fil + '.gz'
        ]
        try:
            file = StringIO.StringIO()
            file.write('%3d\n' % (rank, ))
            for d in dims:
                file.write('%20d ' % (d, ))
            file.write('\n')

            dat = flatten(dat)
            for i in range(dim_max):
                file.write('%s\n' % (dat[i], ))
            file.flush()
            buffer = file.getvalue()
            file.close()
            file = GzipFile(filename=l_filename[0], mode='wb')
            file.write(buffer.encode())
            file.close()
            os.rename(l_filename[0], l_filename[1])
        except:
            self.error('write_array_ch', 'Unable to write ' + l_filename[1])

    LIBRARY = '/home/addman/Software/EZFIO/'


#   EZFIO is an automatic generator of I/O libraries
#   Copyright (C) 2009 Anthony SCEMAMA, CNRS
#
#   This program is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation; either version 2 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License along
#   with this program; if not, write to the Free Software Foundation, Inc.,
#   51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#
#   Anthony Scemama
#   LCPQ - IRSAMC - CNRS
#   Universite Paul Sabatier
#   118, route de Narbonne
#   31062 Toulouse Cedex 4
#   scemama@irsamc.ups-tlse.fr

ezfio = ezfio_obj()


def main():
    import pprint
    import sys
    import os

    try:
        EZFIO_FILE = os.environ['EZFIO_FILE']
    except KeyError:
        print('EZFIO_FILE not defined')
        return 1

    ezfio.set_file(EZFIO_FILE)

    command = '_'.join(sys.argv[1:]).lower()

    try:
        f = getattr(ezfio, command)
    except AttributeError:
        print('{0} not found'.format(command))
        return 1

    if command.startswith('has'):
        if f(): return 0
        else: return 1

    elif command.startswith('get'):
        result = f()
        pprint.pprint(result, width=60, depth=3, indent=4)
        return 0

    elif command.startswith('set'):
        text = sys.stdin.read()
        true = True
        false = False
        TRUE = True
        FALSE = False
        T = True
        F = False
        try:
            data = eval(text)
        except NameError:
            data = text
        except:
            print('Syntax Error')
            return 1
        if data is None:
            data = 'None'
        f(data)
        return 0

    else:
        return 1


if __name__ == '__main__':
    rc = main()
    sys.exit(rc)
