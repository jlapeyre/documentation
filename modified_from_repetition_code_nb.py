from qiskit_aer import AerSimulator

# Qiskit imports
from qiskit import (
    QuantumCircuit,
    QuantumRegister,
    ClassicalRegister,
)

# Qiskit Runtime
from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2 as Sampler

try:
    service
except:
    print("starting service")
    service = QiskitRuntimeService()

############

num_qubits = 5

try:
    rbackend
except:
    print("getting backend")
    rbackend = service.least_busy(
        operational=True,
        simulator=False,
        min_num_qubits=num_qubits,
        dynamic_circuits=True,
    )
    backend = AerSimulator.from_backend(rbackend)


#########

# A single-qubit state will be encoded in three qubits.
qreg_encoded = QuantumRegister(3)

# The first code qubit is initialized with the data (a state) to be encoded.
# The remaining two are initialized to |0>.
qubit_to_encode = qreg_encoded[0]

# Two qubits will read the syndrome.
qreg_syndrome = QuantumRegister(2)

# Register to store the syndrome measurement
creg_syndrome = ClassicalRegister(2, name="syndrome")

# To check that encoding and decoding worked, we will
# read the final state of the encoded data into this register.
creg_encoded = ClassicalRegister(3, name="encoded")

# ancillas_data = qreg_data[1:]

# Create a circuit populated with the registers above.
def initialize_qc(qreg_data, qreg_measure, creg_data, creg_syndrome):
    return QuantumCircuit(qreg_data, qreg_measure, creg_data, creg_syndrome)


# Prepare the state to be encoded. This can be any one-qubit state.
# In our example, we prepare the state |1>.
def prepare_data_state(circuit: QuantumCircuit, qreg_encoded):
    qbit_to_encode = qreg_encoded[0]
    circuit.x(qbit_to_encode)
    circuit.barrier(qreg_encoded)
    return circuit


# Encode the data in the first qubit in the
# first three qubits.
def encode_data(circuit, qreg_encoded) -> QuantumCircuit:
    qbit_to_encode = qreg_encoded[0]
    (syndrome_1, syndrome_2) = qreg_encoded[1:3]
    circuit.cx(qbit_to_encode, syndrome_1)
    circuit.cx(qbit_to_encode, syndrome_2)
    circuit.barrier(qreg_encoded)
    return circuit


def measure_syndrome(qc, qreg_encoded, qreg_syndrome, creg_syndrome):
    """
    Measure the syndrome by measuring the parity.
    We reset our ancilla qubits after measuring the stabilizer
    so we can reuse them for repeated stabilizer measurements.
    Because we have already observed the state of the qubit,
    we can write the conditional reset protocol directly to
    avoid another round of qubit measurement if we used
    the `reset` instruction.
    """

    # Store the parity of code qubits 0 and 1 in the the
    # first syndrome qubit.
    qc.cx(qreg_encoded[0], qreg_syndrome[0])
    qc.cx(qreg_encoded[1], qreg_syndrome[0])

    # Store the parity of code qubits 1 and 2 in the the
    # second syndrome qubit.
    qc.cx(qreg_encoded[0], qreg_syndrome[1])
    qc.cx(qreg_encoded[2], qreg_syndrome[1])

    qc.barrier(*qreg_encoded, *qreg_syndrome)

    # Measure the syndrome qubits into the classical
    # register.
    qc.measure(qreg_syndrome, creg_syndrome)

    # Why? There is probably a good reason
    # # Reset the syndrome qubits to |0>.
    # with qc.if_test((creg_syndrome[0], 1)):
    #     qc.x(qreg_syndrome[0])
    # with qc.if_test((creg_syndrome[1], 1)):
    #     qc.x(qreg_syndrome[1])

    qc.barrier(*qreg_encoded, *qreg_syndrome)
    return qc


def correct_error(circuit, qreg_data, creg_syndrome):
    """We can detect where an error occurred and correct our state"""
    with circuit.if_test((creg_syndrome, 3)):
        circuit.x(qreg_data[0])
    with circuit.if_test((creg_syndrome, 1)):
        circuit.x(qreg_data[1])
    with circuit.if_test((creg_syndrome, 2)):
        circuit.x(qreg_data[2])
    circuit.barrier(qreg_data)
    return circuit


def measure_encoded_state(circuit, qreg_data, creg_data):
    """Read out the final measurements"""
    circuit.barrier(qreg_data)
    circuit.measure(qreg_data, creg_data)
    return circuit


