// Student H - Matrix operations
// CSC 201 - Linear Algebra Programming

#include <iostream>
#include <vector>
#include <stdexcept>

class Matrix {
private:
    int rows, cols;
    std::vector<std::vector<double>> data;

public:
    Matrix(int rows, int cols) : rows(rows), cols(cols) {
        data.resize(rows, std::vector<double>(cols, 0.0));
    }

    void set(int r, int c, double val) {
        if (r < 0 || r >= rows || c < 0 || c >= cols)
            throw std::out_of_range("Index out of range");
        data[r][c] = val;
    }

    double get(int r, int c) const {
        if (r < 0 || r >= rows || c < 0 || c >= cols)
            throw std::out_of_range("Index out of range");
        return data[r][c];
    }

    Matrix add(const Matrix& other) const {
        if (rows != other.rows || cols != other.cols)
            throw std::invalid_argument("Matrix dimensions must match");
        Matrix result(rows, cols);
        for (int i = 0; i < rows; i++)
            for (int j = 0; j < cols; j++)
                result.data[i][j] = data[i][j] + other.data[i][j];
        return result;
    }

    Matrix multiply(const Matrix& other) const {
        if (cols != other.rows)
            throw std::invalid_argument("Invalid dimensions for multiplication");
        Matrix result(rows, other.cols);
        for (int i = 0; i < rows; i++)
            for (int j = 0; j < other.cols; j++)
                for (int k = 0; k < cols; k++)
                    result.data[i][j] += data[i][k] * other.data[k][j];
        return result;
    }

    Matrix transpose() const {
        Matrix result(cols, rows);
        for (int i = 0; i < rows; i++)
            for (int j = 0; j < cols; j++)
                result.data[j][i] = data[i][j];
        return result;
    }

    void print() const {
        for (int i = 0; i < rows; i++) {
            for (int j = 0; j < cols; j++)
                std::cout << data[i][j] << "\t";
            std::cout << std::endl;
        }
    }
};

int main() {
    Matrix a(2, 2);
    a.set(0, 0, 1); a.set(0, 1, 2);
    a.set(1, 0, 3); a.set(1, 1, 4);

    Matrix b(2, 2);
    b.set(0, 0, 5); b.set(0, 1, 6);
    b.set(1, 0, 7); b.set(1, 1, 8);

    std::cout << "Matrix A:" << std::endl;
    a.print();

    std::cout << "Matrix B:" << std::endl;
    b.print();

    std::cout << "A + B:" << std::endl;
    a.add(b).print();

    std::cout << "A * B:" << std::endl;
    a.multiply(b).print();

    std::cout << "Transpose of A:" << std::endl;
    a.transpose().print();

    return 0;
}
