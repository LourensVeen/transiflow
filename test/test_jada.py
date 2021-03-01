import numpy
import pytest
import scipy

from numpy.testing import assert_allclose

from scipy import sparse

from fvm import Continuation
from fvm import Interface

import matplotlib.pyplot as plt

@pytest.fixture(autouse=True, scope='module')
def import_test():
    try:
        from fvm import JadaInterface
    except ImportError:
        pytest.skip('jadapy not found')

@pytest.fixture(scope='module')
def nx():
    return 4

@pytest.fixture(scope='module')
def tol():
    return 1e-7

@pytest.fixture(scope='module')
def atol(tol):
    return tol * 100

@pytest.fixture(scope='module')
def num_evs():
    return 10

@pytest.fixture(scope='module')
def interface(nx):
    dim = 2
    dof = 3
    ny = nx
    nz = 1

    parameters = {'Reynolds Number': 0}
    interface = Interface(parameters, nx, ny, nz, dim, dof)

    return interface

@pytest.fixture(scope='module')
def x(interface):
    n = interface.dof * interface.nx * interface.ny * interface.nz

    parameters = {}
    continuation = Continuation(interface, parameters)

    x0 = numpy.zeros(n)
    x0 = continuation.newton(x0)

    target = 2000
    ds = 100
    maxit = 20
    return continuation.continuation(x0, 'Reynolds Number', target, ds, maxit)

def check_eigenvalues(A_op, B_op, eigs, v, num_evs, tol):
    from jadapy.utils import norm

    A_mat = A_op.mat.todense()
    B_mat = B_op.mat.todense()

    idx = range(len(eigs))
    idx = numpy.array(sorted(idx, key=lambda i: abs(eigs[i])))

    for i in range(num_evs):
        j = idx[i]
        assert norm(A_mat @ v[:, j]) > tol
        assert_allclose(norm(A_mat @ v[:, j] - eigs[j] * B_mat @ v[:, j]), 0, rtol=0, atol=tol)

@pytest.fixture(scope='module')
def arpack_eigs(interface, x, num_evs, tol, atol):
    from fvm import JadaInterface

    A_op = JadaInterface.JadaOp(interface.jacobian(x))
    B_op = JadaInterface.JadaOp(interface.mass_matrix())

    # A_mat = A_op.mat.todense()
    # B_mat = B_op.mat.todense()

    # eigs, v = scipy.linalg.eig(A_mat, B_mat, left=False, right=True)
    eigs, v = sparse.linalg.eigs(A_op, num_evs, B_op, sigma=0.1, tol=tol)

    check_eigenvalues(A_op, B_op, eigs, v, num_evs, atol)
    eigs = numpy.array(sorted(eigs, key=lambda x: abs(x)))
    return eigs[:num_evs]

def test_2D(arpack_eigs, interface, x, num_evs, tol, atol, interactive=False):
    from fvm import JadaInterface
    from jadapy import jdqz

    numpy.random.seed(1234)

    jada_interface = JadaInterface.JadaInterface(interface, x, len(x))
    jac_op = JadaInterface.JadaOp(interface.jacobian(x))
    mass_op = JadaInterface.JadaOp(interface.mass_matrix())

    alpha, beta = jdqz.jdqz(jac_op, mass_op, num_evs, tol=tol, subspace_dimensions=[20, 40])
    jdqz_eigs = numpy.array(sorted(alpha / beta, key=lambda x: abs(x)))

    assert_allclose(jdqz_eigs.real, arpack_eigs.real, rtol=0, atol=atol)
    assert_allclose(abs(jdqz_eigs.imag), abs(arpack_eigs.imag), rtol=0, atol=atol)

    if not interactive:
        return x

    fig1, ax1 = plt.subplots()
    ax1.scatter(eigs.real, eigs.imag, marker='+')
    plt.show()

def test_complex_2D(arpack_eigs, interface, x, num_evs, tol, atol, interactive=False):
    from fvm import JadaInterface
    from jadapy import jdqz

    numpy.random.seed(1234)

    jada_interface = JadaInterface.JadaInterface(interface, x, len(x), numpy.complex128)
    jac_op = JadaInterface.JadaOp(interface.jacobian(x))
    mass_op = JadaInterface.JadaOp(interface.mass_matrix())

    alpha, beta, v = jdqz.jdqz(jac_op, mass_op, num_evs, tol=tol, subspace_dimensions=[20, 40],
                               arithmetic='complex', return_eigenvectors=True)
    check_eigenvalues(jac_op, mass_op, alpha / beta, v, num_evs, atol)

    jdqz_eigs = numpy.array(sorted(alpha / beta, key=lambda x: abs(x)))

    assert_allclose(jdqz_eigs.real, arpack_eigs.real, rtol=0, atol=atol)
    assert_allclose(abs(jdqz_eigs.imag), abs(arpack_eigs.imag), rtol=0, atol=atol)

    if not interactive:
        return x

    fig1, ax1 = plt.subplots()
    ax1.scatter(eigs.real, eigs.imag, marker='+')
    plt.show()
