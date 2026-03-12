/**
 *
 *
 * IDE used:IntelliJ
 *
 * @Author Harsh Prajapati
 * ST# 7354699
 * @Version
 * @Since. 14/11/2025
 */



import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

public class VectorImpTest {

    // Ensures empty constructor creates a vector of length 0.
    @Test
    public void testEmptyConstructorLengthIsZero() {

        VectorImp v = new VectorImp();

        assertEquals(0, v.getLength());

    }
    // Ensures getValue on empty vector throws.
    @Test
    public void testEmptyConstructorGetValueThrows() {

        VectorImp v = new VectorImp();

        assertThrows(IndexOutOfBoundsException.class, () -> v.getValue(0));

    }



    // Constructor (int size, double D)


    // Ensures sized constructor sets correct length.
    @Test
    public void testSizedConstructorCorrectLength() {

        VectorImp v = new VectorImp(5, 3.14);

        assertEquals(5, v.getLength());

    }
    // Ensures sized constructor fills all values with D.
    @Test
    public void testSizedConstructorInitialValuesCorrect() {
        VectorImp v = new VectorImp(3, 2.5);


        assertEquals(2.5, v.getValue(0));


        assertEquals(2.5, v.getValue(1));


        assertEquals(2.5, v.getValue(2));


    }
    // Ensures zero-length sized constructor behaves correctly.
    @Test
    public void testSizedConstructorZeroLengthValid() {


        VectorImp v = new VectorImp(0, 10);


        assertEquals(0, v.getLength());


        assertThrows(IndexOutOfBoundsException.class, () -> v.getValue(0));

    }
    // Ensures negative size throws.
    @Test
    public void testSizedConstructorNegativeThrows() {


        assertThrows(IllegalArgumentException.class, () -> new VectorImp(-5, 1.0));


    }

    // Ensures double[] constructor copies data defensively.
    @Test
    public void testDoubleArrayConstructorCopiesData() {


        double[] arr = {1, 2, 3};


        VectorImp v = new VectorImp(arr);



        arr[0] = 100;// shouldn't affect v


        assertEquals(1, v.getValue(0));


    }
    // Ensures double[] constructor rejects null.
    @Test
    public void testDoubleArrayConstructorNullThrows() {


        assertThrows(IllegalArgumentException.class, () -> new VectorImp((double[]) null));

    }

    // Ensures int[] constructor properly converts to double values.
    @Test
    public void testIntArrayConstructorConvertsCorrectly() {


        int[] arr = {1, 2, 3};


        VectorImp v = new VectorImp(arr);


        assertEquals(1.0, v.getValue(0));


        assertEquals(2.0, v.getValue(1));


        assertEquals(3.0, v.getValue(2));
    }

    // Ensures int[] constructor rejects null.
    @Test
    public void testIntArrayConstructorNullThrows() {

        assertThrows(IllegalArgumentException.class, () -> new VectorImp((int[]) null));

    }



    //  BASIC METHODS

    // Ensures clone() creates a deep copy equal to original.
    @Test
    public void testCloneCreatesDeepCopy() {


        VectorImp v = new VectorImp(new double[]{1, 2});


        Vector clone = v.clone();

        assertTrue(v.equal(clone));


    }
    // Ensures equal() returns true for identical vectors.
    @Test
    public void testEqualTrue() {

        VectorImp v1 = new VectorImp(new double[]{1, 2, 3});


        VectorImp v2 = new VectorImp(new double[]{1, 2, 3});



        assertTrue(v1.equal(v2));
    }
    // Ensures equal() detects differing values.
    @Test
    public void testEqualFalseDifferentValues() {

        VectorImp v1 = new VectorImp(new double[]{1, 2, 3});


        VectorImp v2 = new VectorImp(new double[]{1, 2, 4});


        assertFalse(v1.equal(v2));
    }
    // Ensures equal() detects different lengths.
    @Test
    public void testEqualFalseDifferentSizes() {


        VectorImp v1 = new VectorImp(new double[]{1, 2});


        VectorImp v2 = new VectorImp(new double[]{1, 2, 3});



        assertFalse(v1.equal(v2));
    }



    // APPEND TESTS

    // Ensures append(double[]) concatenates correctly.
    @Test
    public void testAppendDoubleArray() {


        VectorImp v = new VectorImp(new double[]{1, 2});

        Vector result = v.append(new double[]{3, 4});

        assertTrue(result.equal(new VectorImp(new double[]{1, 2, 3, 4})));


    }
    // Ensures append(double[]) rejects null input.
    @Test
    public void testAppendDoubleArrayNullThrows() {


        VectorImp v = new VectorImp(new double[]{1});



        assertThrows(IllegalArgumentException.class, () -> v.append((double[]) null));

    }
    // Ensures append(int[]) concatenates and converts properly.
    @Test
    public void testAppendIntArray() {


        VectorImp v = new VectorImp(new double[]{1, 2});


        Vector result = v.append(new int[]{3, 4});



        assertTrue(result.equal(new VectorImp(new double[]{1, 2, 3, 4})));

    }
    // Ensures append(int[]) rejects null.
    @Test
    public void testAppendIntArrayNullThrows() {


        VectorImp v = new VectorImp(new double[]{1});


        assertThrows(IllegalArgumentException.class, () -> v.append((int[]) null));


    }
    // Ensures append(Vector) works for valid vectors.
    @Test
    public void testAppendVector() {


        VectorImp v1 = new VectorImp(new double[]{1, 2});


        VectorImp v2 = new VectorImp(new double[]{3});



        Vector result = v1.append(v2);


        assertTrue(result.equal(new VectorImp(new double[]{1, 2, 3})));


    }
    // Ensures append(Vector) rejects null argument.
    @Test
    public void testAppendVectorNullThrows() {


        VectorImp v = new VectorImp(new double[]{1});


        assertThrows(IllegalArgumentException.class, () -> v.append((Vector) null));


    }
    // Ensures append(double) adds one scalar to the end.
    @Test
    public void testAppendSingleDouble() {


        VectorImp v = new VectorImp(new double[]{1, 2});


        Vector result = v.append(3.5);



        assertTrue(result.equal(new VectorImp(new double[]{1, 2, 3.5})));


    }



    // ARITHMETIC TESTS



    // add(Vector)
    // Ensures add(Vector) performs elementwise addition.
    @Test
    public void testAddVector() {

        VectorImp v1 = new VectorImp(new double[]{1, 2});


        VectorImp v2 = new VectorImp(new double[]{3, 4});


        Vector result = v1.add(v2);


        assertTrue(result.equal(new VectorImp(new double[]{4, 6})));

    }
    // Ensures add(Vector) throws on length mismatch.
    @Test
    public void testAddVectorDifferentLengthsThrows() {


        VectorImp v1 = new VectorImp(new double[]{1});


        VectorImp v2 = new VectorImp(new double[]{1, 2});



        assertThrows(IllegalArgumentException.class, () -> v1.add(v2));
    }


    // add(double)
    // Ensures add(double) adds scalar to all elements.
    @Test
    public void testAddScalar() {


        VectorImp v = new VectorImp(new double[]{1, 2, 3});


        Vector res = v.add(5);


        assertTrue(res.equal(new VectorImp(new double[]{6, 7, 8})));
    }


    // sub(Vector)
    // Ensures sub(Vector) performs elementwise subtraction.
    @Test
    public void testSubVector() {


        VectorImp v1 = new VectorImp(new double[]{5, 7});


        VectorImp v2 = new VectorImp(new double[]{3, 2});


        Vector result = v1.sub(v2);


        assertTrue(result.equal(new VectorImp(new double[]{2, 5})));
    }
    // Ensures sub(Vector) throws on length mismatch.
    @Test
    public void testSubVectorDifferentLengthsThrows() {


        VectorImp v1 = new VectorImp(new double[]{1});


        VectorImp v2 = new VectorImp(new double[]{1, 2});



        assertThrows(IllegalArgumentException.class, () -> v1.sub(v2));

    }


    // subV(l, r)
    // Ensures subV(l, r) extracts valid subvector.
    @Test
    public void testSubVValid() {


        VectorImp v = new VectorImp(new double[]{10, 20, 30, 40});


        Vector s = v.subV(1, 2);


        assertTrue(s.equal(new VectorImp(new double[]{20, 30})));
    }
    // Ensures subV(l, r) rejects invalid index ranges.
    @Test
    public void testSubVInvalidIndicesThrows() {

        VectorImp v = new VectorImp(new double[]{1, 2, 3});

        assertThrows(IllegalArgumentException.class, () -> v.subV(2, 1));


        assertThrows(IllegalArgumentException.class, () -> v.subV(-1, 1));



        assertThrows(IllegalArgumentException.class, () -> v.subV(0, 5));
    }


    // Mult(Vector)
    // Ensures Mult(Vector) performs elementwise multiplication.
    @Test
    public void testMultVector() {

        VectorImp v1 = new VectorImp(new double[]{2, 3});



        VectorImp v2 = new VectorImp(new double[]{4, 5});


        Vector result = v1.Mult(v2);

        assertTrue(result.equal(new VectorImp(new double[]{8, 15})));

    }
    // Ensures Mult(Vector) rejects mismatched lengths.
    @Test
    public void testMultVectorDifferentLengthsThrows() {


        VectorImp v1 = new VectorImp(new double[]{1});


        VectorImp v2 = new VectorImp(new double[]{1, 2});


        assertThrows(IllegalArgumentException.class, () -> v1.Mult(v2));

    }


    // Mult(double)
    // Ensures Mult(double) multiplies each element by scalar.
    @Test
    public void testMultScalar() {


        VectorImp v = new VectorImp(new double[]{1, 2, 3});



        Vector result = v.Mult(10);

        assertTrue(result.equal(new VectorImp(new double[]{10, 20, 30})));


    }



    // NORMALIZE + DISTANCE
    // Ensures Normalize() returns a unit vector for non-zero input.

    @Test
    public void testNormalizeUnitVector() {


        VectorImp v = new VectorImp(new double[]{3, 4});



        Vector norm = v.Normalize();



        double mag = Math.sqrt(norm.getValue(0) * norm.getValue(0)


                + norm.getValue(1) * norm.getValue(1));

        assertEquals(1.0, mag, 1e-9);

    }
    // Ensures Normalize() returns empty vector for zero vector.
    @Test

    public void testNormalizeZeroVector() {
        VectorImp v = new VectorImp(new double[]{0, 0, 0});


        Vector n = v.Normalize();


        assertEquals(0, n.getLength());


    }
    // Ensures EuclidianDistance() computes correct distance.
    @Test
    public void testEuclideanDistance() {


        VectorImp v1 = new VectorImp(new double[]{0, 0});


        VectorImp v2 = new VectorImp(new double[]{3, 4});


        assertEquals(5.0, v1.EuclidianDistance(v2));


    }
    // Ensures distance throws for mismatched vector sizes.
    @Test
    public void testEuclideanDistanceDifferentLengthsThrows() {


        VectorImp v1 = new VectorImp(new double[]{1});


        VectorImp v2 = new VectorImp(new double[]{1, 2});



        assertThrows(IllegalArgumentException.class, () -> v1.EuclidianDistance(v2));

        
    }
}
