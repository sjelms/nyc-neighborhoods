# Research: Testing Framework Selection

**Date**: 2025-12-02

## 1. Requirement: Testing Framework for Python

The project requires a testing framework to ensure code quality, as outlined by the "IV. Verification & Robustness" principle in the constitution. The implementation plan identified `pytest` as a candidate but marked it as "NEEDS CLARIFICATION". This research validates the choice.

## 2. Decision: Adopt `pytest`

We will use `pytest` as the sole testing framework for this project.

## 3. Rationale

`pytest` is a mature, feature-rich, and widely adopted testing framework in the Python ecosystem. It offers significant advantages over the standard `unittest` library and is a better fit for our project for the following reasons:

*   **Simplicity and Readability**: `pytest` tests are more concise and easier to write and read. It uses plain `assert` statements, which provide detailed output on failure without the need for special `self.assert...` methods.
*   **Powerful Fixture Model**: Fixtures in `pytest` provide a modular and scalable way to manage test setup and teardown, from simple data to complex resources like database connections. This will be crucial for managing dependencies like web requests or file system interactions in our tests.
*   **Rich Plugin Ecosystem**: `pytest` has a vast ecosystem of plugins. For this project, we can immediately benefit from plugins like:
    *   `pytest-cov`: For generating code coverage reports.
    *   `pytest-mock`: For easily mocking external services like Wikipedia or NYC Open Data APIs.
*   **Advanced Features**: Features like test parametrization (`@pytest.mark.parametrize`), test marking (`@pytest.mark.slow`), and flexible test discovery will allow us to organize tests effectively as the project grows.
*   **Strong Community and Documentation**: `pytest` is well-documented and has a large community, making it easy to find solutions and best practices.

## 4. Alternatives Considered

*   **`unittest`**: Python's built-in testing framework. It was rejected because it requires more boilerplate code (e.g., subclassing `unittest.TestCase`), its test discovery is less flexible, and its fixtures are less powerful than `pytest`'s.
*   **`nose2`**: Another popular testing framework. While it has some nice features, `pytest` has a larger community, more plugins, and is generally considered the de-facto standard for new Python projects.

## 5. Implementation Notes

*   All new tests will be written using `pytest`.
*   Tests will be placed in the `tests/` directory, mirroring the `src/` directory structure.
*   A `pytest.ini` file will be created at the root to configure test discovery and register custom markers.
*   We will add `pytest`, `pytest-cov`, and `pytest-mock` to our `requirements.txt`.

This decision resolves the "NEEDS CLARIFICATION" item in the implementation plan.
