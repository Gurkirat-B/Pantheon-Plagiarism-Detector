// Student I - Matrix class implementation
// Linear Algebra assignment

#include <iostream>
#include <vector>
#include <stdexcept>

class Mat {
private:
    int numRows, numCols;
    std::vector<std::vector<double>> grid;

public:
    Mat(int numRows, int numCols) : numRows(numRows), numCols(numCols) {
        grid.resize(numRows, std::vector<double>(numCols, 0.0));
    }

    void setValue(int r, int c, double val) {
        if (r < 0 || r >= numRows || c < 0 || c >= numCols)
            throw std::out_of_range("Index out of range");
        grid[r][c] = val;
    }

    double getValue(int r, int c) const {
        if (r < 0 || r >= numRows || c < 0 || c >= numCols)
            throw std::out_of_range("Index out of range");
        return grid[r][c];
    }

    Mat add(const Mat& other) const {
        if (numRows != other.numRows || numCols != other.numCols)
            throw std::invalid_argument("Matrix dimensions must match");
        Mat result(numRows, numCols);
        for (int i = 0; i < numRows; i++)
            for (int j = 0; j < numCols; j++)
                result.grid[i][j] = grid[i][j] + other.grid[i][j];
        return result;
    }

    Mat multiply(const Mat& other) const {
        if (numCols != other.numRows)
            throw std::invalid_argument("Invalid dimensions for multiplication");
        Mat result(numRows, other.numCols);
        for (int i = 0; i < numRows; i++)
            for (int j = 0; j < other.numCols; j++)
                for (int k = 0; k < numCols; k++)
                    result.grid[i][j] += grid[i][k] * other.grid[k][j];
        return result;
    }

    Mat transpose() const {
        Mat result(numCols, numRows);
        for (int i = 0; i < numRows; i++)
            for (int j = 0; j < numCols; j++)
                result.grid[j][i] = grid[i][j];
        return result;
    }

    void display() const {
        for (int i = 0; i < numRows; i++) {
            for (int j = 0; j < numCols; j++)
                std::cout << grid[i][j] << "\t";
            std::cout << std::endl;
        }
    }
};

int main() {
    Mat a(2, 2);
    a.setValue(0, 0, 1); a.setValue(0, 1, 2);
    a.setValue(1, 0, 3); a.setValue(1, 1, 4);

    Mat b(2, 2);
    b.setValue(0, 0, 5); b.setValue(0, 1, 6);
    b.setValue(1, 0, 7); b.setValue(1, 1, 8);

    std::cout << "Matrix A:" << std::endl;
    a.display();

    std::cout << "Matrix B:" << std::endl;
    b.display();

    std::cout << "A + B:" << std::endl;
    a.add(b).display();

    std::cout << "A * B:" << std::endl;
    a.multiply(b).display();

    std::cout << "Transpose of A:" << std::endl;
    a.transpose().display();

    return 0;
}
