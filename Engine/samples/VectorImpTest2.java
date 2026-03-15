/**
 * Assignment 2 - COSC 4P01
 * @author - Spandan Bhattarai
 * Date - November 13, 2025
 * student Number: 7258551
 */
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

/**
 * Unit tests for the VectorImp class.
 * These tests verify:
 *     Constructors
 *     Basic accessors
 *     Append operations
 *     Equality and cloning behavior
 *     Arithmetic methods (add, sub, Mult)
 *     Subvector extraction (subV)
 *     Normalization and Euclidean distance
 *     Proper handling of invalid inputs
 * The tests also ensure that VectorImp objects operations must not change the original vector.
 */

public class VectorImpTest {

    /**
     * Default constructor should create an empty vector of length 0.
     */
    @Test
    void emptyConstructorCreatesZeroLengthVector() {
        Vector v = new VectorImp();
        assertEquals(0, v.getLength());
    }

    /**
     * Sized constructor should fill all entries with the given value D.
     */
    @Test
    void sizedFillsWithD() {
        Vector v = new VectorImp(3, 2.5);
        assertEquals(3, v.getLength());
        assertEquals(2.5, v.getValue(0));
        assertEquals(2.5, v.getValue(1));
        assertEquals(2.5, v.getValue(2));
    }

    /**
     * Sized constructor should reject a negative size.
     */
    @Test
    void sizedRejectsNegativeSize() {
        assertThrows(IllegalArgumentException.class,
                () -> new VectorImp(-1, 1.0));
    }

    /**
     * getValue should throw an exception when called with out-of-range values.
     */
    @Test
    void getValues(){
        Vector v = new VectorImp(2, 1.0);
        assertThrows(IndexOutOfBoundsException.class, () -> v.getValue(-1));
        assertThrows(IndexOutOfBoundsException.class, () -> v.getValue(2));
    }

    /**
     * double[] constructor should copy values correctly and make a copy.
     */
    @Test
    void doubleArrayConstructorCopiesValues(){
        double[] src = new double[]{1.0, 2.0, 3.0};
        Vector v = new VectorImp(src);

        assertEquals(3, v.getLength());
        assertEquals(1.0, v.getValue(0));
        assertEquals(2.0, v.getValue(1));
        assertEquals(3.0, v.getValue(2));

        src[0] = 99.0;               //Changing src should not change v
        assertEquals(1.0, v.getValue(0));
    }

    /**
     * double[] constructor should reject null input.
     */
    @Test
    void doubleArrayConstructorRejectsNull(){
        assertThrows(IllegalArgumentException.class, () -> new VectorImp((double[]) null));
    }

    /**
     * int[] constructor should copy and convert int values to double,
     */
    @Test
    void intArrayConstructorCopiesAndConvertsValues() {
        int[] src = {1, 2, 3};
        Vector v = new VectorImp(src);
        assertEquals(3, v.getLength());
        assertEquals(1.0, v.getValue(0));
        assertEquals(2.0, v.getValue(1));
        assertEquals(3.0, v.getValue(2));

        src[0] = 99;
        assertEquals(1.0, v.getValue(0));
    }

    /**
     * int[] constructor should reject null input.
     */
    @Test
    void intArrayConstructorRejectsNull() {
        assertThrows(IllegalArgumentException.class,
                () -> new VectorImp((int[]) null));
    }

    /**
     * append(double[]) should add all elements of the array to the end of the vector.
     */
    @Test
    void appendDoubleArrayAddsValues() {
        Vector v = new VectorImp(new double[]{1.0, 2.0});
        Vector r = v.append(new double[]{3.0, 4.0});
        assertEquals(4, r.getLength());
        assertEquals(1.0, r.getValue(0));
        assertEquals(2.0, r.getValue(1));
        assertEquals(3.0, r.getValue(2));
        assertEquals(4.0, r.getValue(3));
    }

    /**
     * Append(double[]) should not modify the original vector.
     */
    @Test
    void appendDoubleArrayDoesNotModifyVector() {
        Vector v = new VectorImp(new double[]{1.0, 2.0});
        Vector r = v.append(new double[]{3.0});
        // original unchanged
        assertEquals(2, v.getLength());
        assertEquals(1.0, v.getValue(0));
        assertEquals(2.0, v.getValue(1));

        assertEquals(3, r.getLength());             // new vector has extra element
        assertEquals(3.0, r.getValue(2));
    }

    /**
     * append(double[]) should reject a null array.
     */
    @Test
    void appendDoubleArrayRejectsNull() {
        Vector v = new VectorImp(new double[]{1.0, 2.0});
        assertThrows(IllegalArgumentException.class, () -> v.append((double[]) null));
    }

    /**
     * append(int[]) should add all converted elements (int to double) at the end.
     */
    @Test
    void appendIntArrayAddsConvertedValues() {
        Vector v = new VectorImp(new double[]{1.0});
        Vector r = v.append(new int[]{2, 3});

        assertEquals(3, r.getLength());
        assertEquals(1.0, r.getValue(0));
        assertEquals(2.0, r.getValue(1));
        assertEquals(3.0, r.getValue(2));
    }

    /**
     * append(int[]) should not modify the original vector.
     */
    @Test
    void appendIntArrayDoesNotModifyOriginalVector() {
        Vector v = new VectorImp(new double[]{5.0});
        Vector r = v.append(new int[]{10});

        assertEquals(1, v.getLength());
        assertEquals(5.0, v.getValue(0));
        assertEquals(2, r.getLength());
        assertEquals(10.0, r.getValue(1));
    }

    /**
     * append(int[]) should reject a null array.
     */
    @Test
    void appendIntArrayRejectsNull() {
        Vector v = new VectorImp(new double[]{1.0});
        assertThrows(IllegalArgumentException.class,
                () -> v.append((int[]) null));
    }

    /**
     * append(Vector) should concatenate all elements of the vector to this one.
     */
    @Test
    void appendVectorAddsAllElements() {
        Vector v1 = new VectorImp(new double[]{1.0, 2.0});
        Vector v2 = new VectorImp(new double[]{3.0, 4.0, 5.0});
        Vector r = v1.append(v2);

        assertEquals(5, r.getLength());
        assertEquals(1.0, r.getValue(0));
        assertEquals(2.0, r.getValue(1));
        assertEquals(3.0, r.getValue(2));
        assertEquals(4.0, r.getValue(3));
        assertEquals(5.0, r.getValue(4));
    }

    /**
     * append(Vector) should not modify either of the original vectors.
     */
    @Test
    void appendVectorDoesNotModifyOriginals() {
        Vector v1 = new VectorImp(new double[]{1.0});
        Vector v2 = new VectorImp(new double[]{2.0});
        Vector r = v1.append(v2);

        assertEquals(1, v1.getLength());
        assertEquals(1.0, v1.getValue(0));
        assertEquals(1, v2.getLength());
        assertEquals(2.0, v2.getValue(0));
        assertEquals(2, r.getLength());
        assertEquals(1.0, r.getValue(0));
        assertEquals(2.0, r.getValue(1));
    }

    /**
     * append(Vector) should reject a null vector.
     */
    @Test
    void appendVectorRejectsNull() {
        Vector v = new VectorImp(new double[]{1.0});
        assertThrows(IllegalArgumentException.class,
                () -> v.append((Vector) null));
    }

    /**
     * append(double) should add a single scalar value to the end.
     */
    @Test
    void appendScalarAddsSingleValueAtEnd() {
        Vector v = new VectorImp(new double[]{1.0, 2.0});
        Vector r = v.append(5.0);

        assertEquals(3, r.getLength());
        assertEquals(1.0, r.getValue(0));
        assertEquals(2.0, r.getValue(1));
        assertEquals(5.0, r.getValue(2));
    }

    /**
     * append(double) should not modify the original vector.
     */
    @Test
    void appendScalarDoesNotModifyOriginalVector() {
        Vector v = new VectorImp(new double[]{1.0});
        Vector r = v.append(7.0);

        assertEquals(1, v.getLength());
        assertEquals(1.0, v.getValue(0));
        assertEquals(2, r.getLength());
        assertEquals(7.0, r.getValue(1));
    }

    /**
     * equal() should return true for vectors with the same length and values.
     */
    @Test
    void equalReturnsTrueForSameValuesAndLength() {
        Vector v1 = new VectorImp(new double[]{1.0, 2.0, 3.0});
        Vector v2 = new VectorImp(new double[]{1.0, 2.0, 3.0});

        assertTrue(v1.equal(v2));
        assertTrue(v2.equal(v1));
    }

    /**
     * equal() should return false for different lengths or different element values.
     */
    @Test
    void equalReturnsFalseForDifferentLengthsOrValues() {
        Vector v1 = new VectorImp(new double[]{1.0, 2.0, 3.0});
        Vector v2 = new VectorImp(new double[]{1.0, 2.0});       // shorter
        Vector v3 = new VectorImp(new double[]{1.0, 99.0, 3.0}); // different middle

        assertFalse(v1.equal(v2));
        assertFalse(v1.equal(v3));
    }

    /**
     * equal() should return false when comparing with null.
     */
    @Test
    void equalReturnsFalseForNull() {
        Vector v1 = new VectorImp(new double[]{1.0});
        assertFalse(v1.equal(null));
    }

    /**
     * clone() should produce a vector with the same values as the original.
     */
    @Test
    void cloneProducesEqualVectorWithSameValues() {
        Vector v1 = new VectorImp(new double[]{1.0, 2.0, 3.0});
        Vector v2 = v1.clone();

        assertTrue(v1.equal(v2));  // same contents
    }

    /**
     * clone() should return a different object
     */
    @Test
    void cloneProducesDifferentObject() {
        Vector v1 = new VectorImp(new double[]{1.0, 2.0});
        Vector v2 = v1.clone();

        assertNotSame(v1, v2);          // same values but not the same reference
    }

    /**
     * add(Vector) should perform element-wise addition.
     */
    @Test
    void addVectorAddsElementWise() {
        Vector v1 = new VectorImp(new double[]{1.0, 2.0});
        Vector v2 = new VectorImp(new double[]{3.0, 4.0});
        Vector r = v1.add(v2);

        assertEquals(2, r.getLength());
        assertEquals(4.0, r.getValue(0));
        assertEquals(6.0, r.getValue(1));
    }

    /**
     * add(Vector) should not modify the original vectors.
     */
    @Test
    void addVectorDoesNotModifyOriginals() {
        Vector v1 = new VectorImp(new double[]{1.0, 2.0});
        Vector v2 = new VectorImp(new double[]{3.0, 4.0});

        Vector r = v1.add(v2);

        // originals unchanged
        assertEquals(1.0, v1.getValue(0));
        assertEquals(2.0, v1.getValue(1));
        assertEquals(3.0, v2.getValue(0));
        assertEquals(4.0, v2.getValue(1));
    }

    /**
     * add(Vector) should reject null or vectors of different lengths.
     */
    @Test
    void addVectorRejectsNullOrSizeMismatch() {
        Vector v1 = new VectorImp(new double[]{1.0, 2.0});
        Vector v2 = new VectorImp(new double[]{1.0});

        assertThrows(IllegalArgumentException.class,
                () -> v1.add((Vector) null));
        assertThrows(IllegalArgumentException.class,
                () -> v1.add(v2));
    }

    /**
     * add(double) should add the scalar to each element.
     */
    @Test
    void addScalarAddsToEachElement() {
        Vector v = new VectorImp(new double[]{1.0, -2.0, 3.0});
        Vector r = v.add(10.0);

        assertEquals(3, r.getLength());
        assertEquals(11.0, r.getValue(0));
        assertEquals(8.0, r.getValue(1));
        assertEquals(13.0, r.getValue(2));
    }

    /**
     * add(double) should not modify the original vector.
     */
    @Test
    void addScalarDoesNotModifyOriginal() {
        Vector v = new VectorImp(new double[]{1.0, 2.0});
        Vector r = v.add(5.0);

        assertEquals(1.0, v.getValue(0));
        assertEquals(2.0, v.getValue(1));
        assertEquals(6.0, r.getValue(0));
        assertEquals(7.0, r.getValue(1));
    }

    /**
     * sub(Vector) should perform element-wise subtraction
     */
    @Test
    void subVectorSubtractsElementWise() {
        Vector v1 = new VectorImp(new double[]{5.0, 7.0});
        Vector v2 = new VectorImp(new double[]{2.0, 3.0});
        Vector r = v1.sub(v2);

        assertEquals(2, r.getLength());
        assertEquals(3.0, r.getValue(0));
        assertEquals(4.0, r.getValue(1));
    }

    /**
     * sub(Vector) should reject vectors of different lengths.
     */
    @Test
    void subVectorRejectsNullOrSizeMismatch() {
        Vector v1 = new VectorImp(new double[]{1.0, 2.0});
        Vector v2 = new VectorImp(new double[]{1.0});

        assertThrows(IllegalArgumentException.class, () -> v1.sub((Vector) null));
        assertThrows(IllegalArgumentException.class, () -> v1.sub(v2));
    }

    /**
     * subV(l, r) should return a correct subvector range [l, r].
     */
    @Test
    void subVReturnsCorrectRange() {
        Vector v = new VectorImp(new double[]{10.0, 20.0, 30.0, 40.0});
        Vector sub = v.subV(1, 3);

        assertEquals(3, sub.getLength());
        assertEquals(20.0, sub.getValue(0));
        assertEquals(30.0, sub.getValue(1));
        assertEquals(40.0, sub.getValue(2));
    }

    /**
     * subV(l, r) should reject invalid ranges
     */
    @Test
    void subVRejectsInvalidRanges() {
        Vector v = new VectorImp(new double[]{1.0, 2.0, 3.0});

        assertThrows(IllegalArgumentException.class, () -> v.subV(-1, 1)); // negative l
        assertThrows(IllegalArgumentException.class, () -> v.subV(2, 1));  // r < l
        assertThrows(IllegalArgumentException.class, () -> v.subV(0, 3));  // r >= length
    }

    /**
     * Mult(Vector) should perform element-wise multiplication.
     */
    @Test
    void multVectorDoesElementWiseProduct() {
        Vector v1 = new VectorImp(new double[]{2.0, 3.0});
        Vector v2 = new VectorImp(new double[]{4.0, 5.0});
        Vector r = v1.Mult(v2);

        assertEquals(2, r.getLength());
        assertEquals(8.0, r.getValue(0));   // 2 * 4
        assertEquals(15.0, r.getValue(1));  // 3 * 5
    }

    /**
     * Mult(Vector) should reject size-mismatched vectors.
     */
    @Test
    void multVectorRejectsNullOrSizeMismatch() {
        Vector v1 = new VectorImp(new double[]{1.0, 2.0});
        Vector v2 = new VectorImp(new double[]{1.0});

        assertThrows(IllegalArgumentException.class, () -> v1.Mult((Vector) null));
        assertThrows(IllegalArgumentException.class, () -> v1.Mult(v2));
    }

    /**
     * Mult(double) should multiply each element by the scalar.
     */
    @Test
    void multScalarMultipliesEachElement() {
        Vector v = new VectorImp(new double[]{1.0, -2.0, 3.0});
        Vector r = v.Mult(3.0);

        assertEquals(3, r.getLength());
        assertEquals(3.0, r.getValue(0));
        assertEquals(-6.0, r.getValue(1));
        assertEquals(9.0, r.getValue(2));
    }

    /**
     * Mult(double) should not modify the original vector.
     */
    @Test
    void multScalarDoesNotModifyOriginal() {
        Vector v = new VectorImp(new double[]{1.0, 2.0});
        Vector r = v.Mult(4.0);

        assertEquals(1.0, v.getValue(0));
        assertEquals(2.0, v.getValue(1));
        assertEquals(4.0, r.getValue(0));
        assertEquals(8.0, r.getValue(1));
    }

    /**
     * Normalize() should produce a unit vector
     */
    @Test
    void normalizeProducesUnitVector() {
        Vector v = new VectorImp(new double[]{3.0, 4.0}); // length 5
        Vector n = v.Normalize();
        // length of normalized vector should be (approximately) 1
        double len = Math.sqrt(
                n.getValue(0) * n.getValue(0) +
                        n.getValue(1) * n.getValue(1)
        );
        assertEquals(1.0, len, 1e-9);
    }

    /**
     * Normalize() should throw if called on a zero vector.
     */
    @Test
    void normalizeZeroVectorThrows() {
        Vector v = new VectorImp(new double[]{0.0, 0.0});
        assertThrows(IllegalStateException.class, v::Normalize);
    }

    /**
     * EuclidianDistance() should compute the correct distance between two vectors.
     */
    @Test
    void euclidianDistanceComputesCorrectValue() {
        Vector v1 = new VectorImp(new double[]{0.0, 0.0});
        Vector v2 = new VectorImp(new double[]{3.0, 4.0});

        double d = v1.EuclidianDistance(v2);
        assertEquals(5.0, d, 1e-9);  //triangle
    }

    /**
     * EuclidianDistance() should reject null vectors or vectors of different lengths.
     */
    @Test
    void euclidianDistanceRejectsNullOrSizeMismatch() {
        Vector v1 = new VectorImp(new double[]{0.0});
        Vector v2 = new VectorImp(new double[]{0.0, 1.0});

        assertThrows(IllegalArgumentException.class, () -> v1.EuclidianDistance(null));
        assertThrows(IllegalArgumentException.class, () -> v1.EuclidianDistance(v2));
    }
}

