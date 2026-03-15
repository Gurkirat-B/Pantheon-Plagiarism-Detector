/*
 * Author: Heet Patel
 * Student# 6857965
 * COSC 4P01 - Assignment 2*/
package vector;

import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

public class VectorImpTest
{
    @Test //tests length of a regular vector
    void testGetLength()
    {
        Vector v = new VectorImp(new double[]{1.0, 2.0, 3.0});
        assertEquals(3, v.getLength());
    }

    @Test //tests reading a value at a given index
    void testGetValue()
    {
        Vector v= new VectorImp(new double[]{5.5, 6.6, 7.7});
        assertEquals(6.6, v.getValue(1));
    }

    @Test //Testing appending a double[] onto a vector
    void testAppendDoubleArray()
    {
        Vector v= new VectorImp(new double[]{1.0, 2.0});
        Vector result = v.append(new double[]{3.0, 4.0});
        assertEquals(4, result.getLength());
        assertEquals(3.0, result.getValue(2));
        assertEquals(4.0, result.getValue(3));
    }

    @Test //testing appending an int[] and converting to doubles
    void testAppendIntArray()
    {
        Vector v= new VectorImp(new double[]{1.0});
        Vector result= v.append(new int[]{2, 3});
        assertEquals(3, result.getLength());
        assertEquals(3.0, result.getValue(2));
    }

    @Test //tets appending one vector to another
    void testAppendVector()
    {
        Vector v1= new VectorImp(new double[]{1.0, 2.0});
        Vector v2= new VectorImp(new double[]{3.0, 4.0});
        Vector result= v1.append(v2);
        assertEquals(4, result.getLength());
        assertEquals(4.0, result.getValue(3));
    }


    @Test //tests appending a single double vector
    void testAppendSingleDouble()
    {
        Vector v = new VectorImp(new double[]{5.0});
        Vector result= v.append(6.0);
        assertEquals(2, result.getLength());
        assertEquals(6.0, result.getValue(1));
    }

    @Test //tests vector + vector addition
    void testAddVector()
    {
        Vector v1= new VectorImp(new double[]{1.0, 2.0, 3.0});
        Vector v2= new VectorImp(new double[]{4.0, 5.0, 6.0});
        Vector result= v1.add(v2);
        assertEquals(5.0, result.getValue(0));
        assertEquals(7.0, result.getValue(1));
        assertEquals(9.0, result.getValue(2));
    }

    @Test // tests adding a scalar to all vector elements
    void testAddDouble()
    {
        Vector v= new VectorImp(new double[]{1.0, 2.0, 3.0});
        Vector result= v.add(2.0);
        assertEquals(3.0, result.getValue(0));
        assertEquals(4.0, result.getValue(1));
        assertEquals(5.0, result.getValue(2));
    }

    @Test //testing subtracting one vector from another
    void testSubVector()
    {
        Vector v1= new VectorImp(new double[]{5.0, 7.0, 9.0});
        Vector v2= new VectorImp(new double[]{1.0, 2.0, 3.0});
        Vector result= v1.sub(v2);
        assertEquals(4.0, result.getValue(0));
        assertEquals(5.0, result.getValue(1));
        assertEquals(6.0, result.getValue(2));
    }

    @Test //tests elemetn-by-element multiplication of two vectors
    void testMultVector()
    {
        Vector v1 = new VectorImp(new double[]{1.0, 2.0, 3.0});
        Vector v2= new VectorImp(new double[]{2.0, 3.0, 4.0});
        Vector result= v1.Mult(v2);
        assertEquals(2.0, result.getValue(0));
        assertEquals(6.0, result.getValue(1));
        assertEquals(12.0, result.getValue(2));
    }

    @Test //tests scalar multiplication on the vector
    void testMultDouble()
    {
        Vector v= new VectorImp(new double[]{1.0, 2.0, 3.0});
        Vector result= v.Mult(2.0);
        assertEquals(2.0, result.getValue(0));
        assertEquals(4.0, result.getValue(1));
        assertEquals(6.0, result.getValue(2));
    }

    @Test // tests normalizing a vector to unit length
    void testNormalize()
    {
        Vector v = new VectorImp(new double[]{3.0, 4.0});
        Vector normalized= v.Normalize();
        assertEquals(1.0,
                Math.round(normalized.getValue(0) * 10) / 10.0 + Math.round(normalized.getValue(1) * 10) / 10.0, 1);
        assertEquals(1.0,
                Math.round(Math.sqrt(Math.pow(normalized.getValue(0), 2) + Math.pow(normalized.getValue(1), 2)) * 10) / 10.0, 0.1);
    }

    @Test //tests Euclidian distance calculation
    void testEuclidianDistance()
    {
        Vector v1= new VectorImp(new double[]{1.0, 2.0, 3.0});
        Vector v2= new VectorImp(new double[]{4.0, 6.0, 3.0});
        assertEquals(5.0, v1.EuclidianDistance(v2));
    }

    @Test //tests extracting a subvector between two indexes
    void testSubV()
    {
        Vector v= new VectorImp(new double[]{1.0, 2.0, 3.0, 4.0, 5.0});
        Vector sub= v.subV(1,3);
        assertEquals(3, sub.getLength());
        assertEquals(2.0, sub.getValue(0));
        assertEquals(4.0, sub.getValue(2));
    }


    @Test //tests checking vector equality
    void testEqual()
    {
        Vector v1= new VectorImp(new double[]{1.0, 2.0, 3.0});
        Vector v2= new VectorImp(new double[]{1.0, 2.0, 3.0});
        assertTrue(v1.equal(v2));
    }

    @Test //tests cloning a vector
    void testClone()
    {
        Vector v1= new VectorImp(new double[]{2.0, 4.0, 6.0});
        Vector v2= v1.clone();
        assertTrue(v1.equal(v2));
        assertNotSame(v1, v2);
    }

    @Test //tests default empty constructor creates a size 0 vector
    void testDefaultConstructor()
    {
        Vector v= new VectorImp();
        assertEquals(0, v.getLength());
    }

    @Test //tests double[] constructor copies values correctly
    void DoubleArrayConstructor()
    {
        Vector v= new VectorImp(new double[]{1.5, 2.5, 3.5});
        assertEquals(3, v.getLength());
        assertEquals(1.5, v.getValue(0));
        assertEquals(3.5, v.getValue(2));
    }

    @Test // tests (size, fillValue) constructor initializes all elements
    void testSizeAndFillConstructor()
    {
        Vector v= new VectorImp(4, 7.0);
        assertEquals(4, v.getLength());
        assertEquals(7.0, v.getValue(0));
        assertEquals(7.0, v.getValue(3));
    }


    @Test // tests int[] constructor converting to double elements
    void testIntArrayConstructor()
    {
        Vector v= new VectorImp(new int[]{1, 2, 3, 4});
        assertEquals(4, v.getLength());
        assertEquals(1.0, v.getValue(0));
        assertEquals(4.0, v.getValue(3));
    }

    @Test // tests getValue, throws error for negative index
    void testFetValueNegativeIndex()
    {
        Vector v= new VectorImp(new double[]{1.0, 2.0});
        assertThrows(IndexOutOfBoundsException.class, () -> v.getValue(-1));
    }

    @Test // test getValue, throws error when index is too large
    void testGetValueIndexTooLarge()
    {
        Vector v= new VectorImp(new double[]{1.0, 2.0});
        assertThrows(IndexOutOfBoundsException.class, () -> v.getValue(5));
    }

    @Test //tests add(), throws error when vectors have different lengths
    void testAddDifferentLenghts()
    {
        Vector v1= new VectorImp(new double[]{1.0, 2.0});
        Vector v2= new VectorImp(new double[]{1.0, 2.0, 3.0});
        assertThrows(IllegalArgumentException.class, () -> v1.add(v2));
    }

    @Test //test sub(), throws error for different vector sizes
    void testSubDifferentLengths()
    {
        Vector v1= new VectorImp(new double[]{1.0});
        Vector v2 = new VectorImp(new double[]{1.0, 2.0});
        assertThrows(IllegalArgumentException.class, () -> v1.sub(v2));
    }

    @Test // tests Mult(Vector), throws error for size mismatch
    void testMultDifferentLengths()
    {
        Vector v1= new VectorImp(new double[]{1.0, 2.0});
        Vector v2= new VectorImp(new double[]{5.0});
        assertThrows(IllegalArgumentException.class, () -> v1.Mult(v2));
    }

    @Test// tests EuclidianDistance, throws error if lengths differ
    void testEuclidianDistanceDifferentLengths()
    {
        Vector v1= new VectorImp(new double[]{1.0, 2.0});
        Vector v2 = new VectorImp(new double[]{1.0});
        assertThrows(IllegalArgumentException.class,
                () -> v1.EuclidianDistance(v2));
    }

    @Test// tests subV, throws error when left index is negative
    void testSubVLeftOutOfRange()
    {
        Vector v= new VectorImp(new double[]{1, 2, 3});
        assertThrows(IllegalArgumentException.class, () -> v.subV(-1, 2));
    }


    @Test// tests subV, throws error when right index is out of bounds
    void testSubVRightOutOfRange()
    {
        Vector v= new VectorImp(new double[]{1, 2, 3});
        assertThrows(IllegalArgumentException.class, () -> v.subV(0, 5));
    }

    @Test//tests subV, throws error when left index is greater than right
    void testSubVLeftGreaterThanRight()
    {
        Vector v= new VectorImp(new double[]{1, 2, 3});
        assertThrows(IllegalArgumentException.class, () -> v.subV(2, 1));
    }

    @Test//tests Normalize, throws error on a zero vector
    void testNormalizeZeroVector()
    {
        Vector v= new VectorImp(new double[]{0.0, 0.0, 0.0});
        assertThrows(ArithmeticException.class, v::Normalize);
    }

    @Test//tests append on an empty vector
    void testAppendToEmptyVector()
    {
        Vector v= new VectorImp();
        Vector result= v.append(new double[]{5.0});
        assertEquals(1, result.getLength());
        assertEquals(5.0, result.getValue(0));
    }

    @Test//tests distance between two empty vector is zero
    void testDistanceBetweenEmptyVector()
    {
        Vector v1 = new VectorImp();
        Vector v2= new VectorImp();
        assertEquals(0.0, v1.EuclidianDistance(v2));
    }

    @Test//tests add(double) on an empty vector, returns empty vector
    void testAddDoubleToEmptyVector()
    {
        Vector v = new VectorImp();
        Vector result = v.add(10.0);
        assertEquals(0, result.getLength());
    }

    @Test//tests cloning on empty vector
    void testCloneEmptyVector()
    {
        Vector v = new VectorImp();
        Vector c= v.clone();
        assertEquals(0, c.getLength());
        assertTrue(v.equal(c));
    }


}
